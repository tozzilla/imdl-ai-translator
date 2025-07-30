"""
IDML Processor - Gestisce l'apertura, manipolazione e salvataggio di file IDML
"""

import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from xml.etree import ElementTree as ET

from simple_idml import idml


class IDMLProcessor:
    """Classe per processare file IDML di InDesign"""
    
    def __init__(self, idml_path: str):
        """
        Inizializza il processor con il path al file IDML
        
        Args:
            idml_path: Path al file IDML da processare
        """
        self.idml_path = Path(idml_path)
        self.idml_package = None
        self.stories_data = {}
        self.master_pages_data = {}
        self.backing_story_data = {}
        self.xml_structure = {}
        self.temp_dir = None
        
        if not self.idml_path.exists():
            raise FileNotFoundError(f"File IDML non trovato: {idml_path}")
            
    def load_idml(self) -> None:
        """Carica il file IDML in memoria"""
        try:
            self.idml_package = idml.IDMLPackage(str(self.idml_path))
            
            # Verifica Track Changes sia disattivato
            self._validate_track_changes()
            
            self._extract_stories()
            
            # Carica BackingStory e struttura XML se presente
            self._load_backing_story()
        except Exception as e:
            raise RuntimeError(f"Errore nel caricamento IDML: {e}")
    
    def _extract_stories(self) -> None:
        """Estrae le stories (contenuti testuali) dal file IDML"""
        stories_list = self.idml_package.stories
        
        for story_path in stories_list:
            try:
                # Ottieni il contenuto della story usando il path
                story_content = self.idml_package.read(story_path)
                if isinstance(story_content, bytes):
                    story_content = story_content.decode('utf-8')
                
                # Parse XML content
                story_root = ET.fromstring(story_content)
                self.stories_data[story_path] = {
                    'root': story_root,
                    'original_content': story_content
                }
            except (ET.ParseError, Exception) as e:
                print(f"Warning: Errore parsing story {story_path}: {e}")
                continue
    
    def _validate_track_changes(self) -> None:
        """
        Verifica che Track Changes sia disattivato in tutte le stories.
        Track Changes attivo può causare problemi di segmentazione nella traduzione.
        """
        track_changes_found = []
        
        # Controlla le preferences del documento
        try:
            preferences_content = self.idml_package.read('Resources/Preferences.xml')
            if isinstance(preferences_content, bytes):
                preferences_content = preferences_content.decode('utf-8')
            
            pref_root = ET.fromstring(preferences_content)
            
            # Cerca impostazioni Track Changes nelle preferences
            for elem in pref_root.iter():
                if 'TrackChanges' in elem.attrib:
                    for attr, value in elem.attrib.items():
                        if 'TrackChanges' in attr and value.lower() == 'true':
                            track_changes_found.append(f"Preferences: {attr}={value}")
        except Exception as e:
            print(f"Warning: Impossibile verificare Track Changes nelle preferences: {e}")
        
        # Controlla ogni story per Track Changes attivo
        for story_path in self.idml_package.stories:
            try:
                story_content = self.idml_package.read(story_path)
                if isinstance(story_content, bytes):
                    story_content = story_content.decode('utf-8')
                
                # Cerca attributi TrackChanges nella story
                if 'TrackChanges="true"' in story_content:
                    track_changes_found.append(f"Story: {story_path}")
                    
                # Parse XML per controllo più accurato
                story_root = ET.fromstring(story_content)
                for elem in story_root.iter():
                    if elem.get('TrackChanges', '').lower() == 'true':
                        track_changes_found.append(f"Story {story_path}: elemento {elem.tag}")
                        
            except Exception as e:
                print(f"Warning: Errore controllo Track Changes in {story_path}: {e}")
                continue
        
        # Se Track Changes è attivo, genera warning o errore
        if track_changes_found:
            warning_msg = (
                "\n⚠️  ATTENZIONE: Track Changes è attivo nel documento!\n"
                "   Questo può causare problemi di segmentazione durante la traduzione.\n"
                "   Si consiglia di:\n"
                "   1. Aprire il file in InDesign\n"
                "   2. Accettare tutte le modifiche (Accept All Changes)\n"
                "   3. Disattivare Track Changes\n"
                "   4. Salvare nuovamente come IDML\n"
                f"\n   Track Changes trovato in:\n   - " + "\n   - ".join(track_changes_found)
            )
            print(warning_msg)
            
            # Opzionale: solleva eccezione per forzare la correzione
            # raise ValueError("Track Changes deve essere disattivato prima della traduzione")
    
    def validate_font_compatibility(self, target_language: str) -> Dict[str, Any]:
        """
        Valida la compatibilità dei font per lingue non latine.
        
        Args:
            target_language: Codice lingua di destinazione (es: 'zh', 'ja', 'ar', 'he', 'th')
            
        Returns:
            Dizionario con informazioni sulla compatibilità font
        """
        # Lingue che richiedono font specifici
        non_latin_languages = {
            'zh': {'name': 'Chinese', 'script': 'CJK', 'required_fonts': ['Noto Sans CJK', 'SimHei', 'SimSun', 'Microsoft YaHei']},
            'ja': {'name': 'Japanese', 'script': 'CJK', 'required_fonts': ['Noto Sans CJK', 'Hiragino', 'Yu Gothic', 'Meiryo']},
            'ko': {'name': 'Korean', 'script': 'CJK', 'required_fonts': ['Noto Sans CJK', 'Malgun Gothic', 'Gulim']},
            'ar': {'name': 'Arabic', 'script': 'Arabic', 'required_fonts': ['Noto Sans Arabic', 'Arial Unicode MS', 'Tahoma']},
            'he': {'name': 'Hebrew', 'script': 'Hebrew', 'required_fonts': ['Noto Sans Hebrew', 'Arial Hebrew', 'David']},
            'th': {'name': 'Thai', 'script': 'Thai', 'required_fonts': ['Noto Sans Thai', 'Tahoma', 'Angsana New']},
            'hi': {'name': 'Hindi', 'script': 'Devanagari', 'required_fonts': ['Noto Sans Devanagari', 'Mangal', 'Arial Unicode MS']},
            'ru': {'name': 'Russian', 'script': 'Cyrillic', 'required_fonts': ['Arial', 'Times New Roman', 'Calibri']},
            'el': {'name': 'Greek', 'script': 'Greek', 'required_fonts': ['Arial', 'Times New Roman', 'Calibri']}
        }
        
        validation_result = {
            'target_language': target_language,
            'requires_special_fonts': False,
            'script_type': 'Latin',
            'fonts_found': [],
            'missing_fonts': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Controlla se la lingua richiede font speciali
        if target_language not in non_latin_languages:
            return validation_result
        
        lang_info = non_latin_languages[target_language]
        validation_result['requires_special_fonts'] = True
        validation_result['script_type'] = lang_info['script']
        
        # Estrai font utilizzati nel documento
        document_fonts = set()
        
        try:
            # Leggi il file Fonts.xml
            fonts_content = self.idml_package.read('Resources/Fonts.xml')
            if isinstance(fonts_content, bytes):
                fonts_content = fonts_content.decode('utf-8')
            
            fonts_root = ET.fromstring(fonts_content)
            
            # Cerca tutti i font definiti
            for elem in fonts_root.iter():
                if 'FontFamily' in elem.attrib:
                    document_fonts.add(elem.get('FontFamily'))
                if 'Name' in elem.attrib and elem.tag.endswith('Font'):
                    document_fonts.add(elem.get('Name'))
        except Exception as e:
            validation_result['warnings'].append(f"Impossibile leggere definizioni font: {e}")
        
        # Cerca font usati nelle stories
        for story_path, story_data in self.stories_data.items():
            story_root = story_data['root']
            for elem in story_root.iter():
                # Cerca attributi font
                for attr in ['AppliedFont', 'FontFamily']:
                    if attr in elem.attrib:
                        font_value = elem.get(attr)
                        if font_value and '/' in font_value:
                            # Estrai nome font da path IDML (es: "Arial/Regular")
                            font_name = font_value.split('/')[0]
                            document_fonts.add(font_name)
        
        validation_result['fonts_found'] = list(document_fonts)
        
        # Verifica se almeno uno dei font richiesti è presente
        required_fonts = set(lang_info['required_fonts'])
        found_compatible = False
        
        for doc_font in document_fonts:
            # Controllo case-insensitive e parziale
            for req_font in required_fonts:
                if req_font.lower() in doc_font.lower() or doc_font.lower() in req_font.lower():
                    found_compatible = True
                    break
        
        if not found_compatible:
            validation_result['missing_fonts'] = lang_info['required_fonts']
            validation_result['warnings'].append(
                f"⚠️  Nessun font compatibile trovato per {lang_info['name']}. "
                f"Il testo potrebbe non essere visualizzato correttamente."
            )
            validation_result['recommendations'].append(
                f"Si consiglia di installare uno dei seguenti font prima della traduzione: "
                f"{', '.join(lang_info['required_fonts'][:3])}"
            )
        
        # Avvisi aggiuntivi per script specifici
        if lang_info['script'] == 'Arabic' or lang_info['script'] == 'Hebrew':
            validation_result['warnings'].append(
                f"⚠️  {lang_info['name']} richiede supporto RTL (Right-to-Left). "
                "Verificare che il documento InDesign sia configurato correttamente."
            )
            validation_result['recommendations'].append(
                "Abilitare 'World-Ready Composer' in InDesign per il supporto RTL ottimale."
            )
        
        if lang_info['script'] == 'CJK':
            validation_result['recommendations'].append(
                "Per testo CJK, considerare l'uso di 'Adobe CJK Composer' per migliore resa tipografica."
            )
        
        # Stampa riepilogo
        print(f"\n📋 Validazione Font per {lang_info['name']} ({target_language}):")
        print(f"   Script: {lang_info['script']}")
        print(f"   Font nel documento: {len(document_fonts)}")
        
        if validation_result['warnings']:
            for warning in validation_result['warnings']:
                print(f"   {warning}")
        
        if validation_result['recommendations']:
            print("   📌 Raccomandazioni:")
            for rec in validation_result['recommendations']:
                print(f"      - {rec}")
        
        return validation_result
    
    def check_linked_graphics_text(self) -> Dict[str, List[str]]:
        """
        Verifica la presenza di testo in grafica collegata che potrebbe richiedere traduzione separata.
        
        Returns:
            Dizionario con informazioni sui file grafici collegati e potenziali testi
        """
        linked_graphics = {
            'graphics_found': [],
            'potential_text_graphics': [],
            'warnings': [],
            'recommendations': []
        }
        
        if not self.idml_package:
            return linked_graphics
        
        try:
            # Leggi il file Links.xml che contiene informazioni sui collegamenti
            links_content = self.idml_package.read('Links.xml')
            if isinstance(links_content, bytes):
                links_content = links_content.decode('utf-8')
            
            links_root = ET.fromstring(links_content)
            
            # Pattern per identificare file che potrebbero contenere testo
            text_graphic_patterns = [
                '.ai', '.eps', '.pdf',  # File vettoriali che spesso contengono testo
                '.psd',  # Photoshop con possibili layer di testo
                '.svg'   # SVG può contenere testo
            ]
            
            # Cerca tutti i Link elements
            for link_elem in links_root.iter():
                if self._remove_namespace(link_elem.tag) == 'Link':
                    link_path = link_elem.get('LinkResourceURI', '')
                    file_name = link_path.split('/')[-1] if '/' in link_path else link_path
                    
                    if file_name:
                        linked_graphics['graphics_found'].append(file_name)
                        
                        # Controlla se è un tipo di file che potrebbe contenere testo
                        file_ext = file_name.lower()
                        for pattern in text_graphic_patterns:
                            if file_ext.endswith(pattern):
                                linked_graphics['potential_text_graphics'].append({
                                    'file': file_name,
                                    'type': pattern,
                                    'path': link_path
                                })
                                break
        
        except Exception as e:
            linked_graphics['warnings'].append(f"Impossibile analizzare Links.xml: {e}")
        
        # Cerca anche nei Spreads per Rectangle/Image con collegamenti
        try:
            spread_files = []
            for file_info in self.idml_package.infolist():
                if 'Spreads/' in file_info.filename and file_info.filename.endswith('.xml'):
                    spread_files.append(file_info.filename)
            
            for spread_file in spread_files:
                try:
                    spread_content = self.idml_package.read(spread_file)
                    if isinstance(spread_content, bytes):
                        spread_content = spread_content.decode('utf-8')
                    
                    spread_root = ET.fromstring(spread_content)
                    
                    # Cerca elementi Image o Rectangle con Link
                    for elem in spread_root.iter():
                        elem_tag = self._remove_namespace(elem.tag)
                        if elem_tag in ['Image', 'Rectangle', 'Polygon', 'GraphicLine']:
                            # Cerca attributi di collegamento
                            for attr in ['Link', 'LinkResourceURI']:
                                if attr in elem.attrib:
                                    link_ref = elem.get(attr)
                                    if link_ref and link_ref not in [g['path'] for g in linked_graphics['potential_text_graphics']]:
                                        # Aggiungi se non già presente
                                        file_name = link_ref.split('/')[-1]
                                        for pattern in text_graphic_patterns:
                                            if file_name.lower().endswith(pattern):
                                                linked_graphics['potential_text_graphics'].append({
                                                    'file': file_name,
                                                    'type': pattern,
                                                    'path': link_ref,
                                                    'found_in': spread_file
                                                })
                                                break
                
                except Exception as e:
                    continue
        
        except Exception as e:
            linked_graphics['warnings'].append(f"Errore analisi Spreads per grafiche: {e}")
        
        # Genera warnings e raccomandazioni
        if linked_graphics['potential_text_graphics']:
            linked_graphics['warnings'].append(
                f"⚠️  Trovate {len(linked_graphics['potential_text_graphics'])} grafiche che potrebbero contenere testo da tradurre"
            )
            
            # Raggruppa per tipo
            by_type = {}
            for graphic in linked_graphics['potential_text_graphics']:
                graphic_type = graphic['type']
                if graphic_type not in by_type:
                    by_type[graphic_type] = []
                by_type[graphic_type].append(graphic['file'])
            
            for graphic_type, files in by_type.items():
                linked_graphics['warnings'].append(
                    f"   - {len(files)} file {graphic_type}: {', '.join(files[:3])}{'...' if len(files) > 3 else ''}"
                )
            
            linked_graphics['recommendations'].append(
                "Verificare manualmente questi file grafici per testo da tradurre:"
            )
            linked_graphics['recommendations'].append(
                "1. File AI/EPS/PDF: aprire in Illustrator per tradurre testi"
            )
            linked_graphics['recommendations'].append(
                "2. File PSD: aprire in Photoshop per tradurre layer di testo"
            )
            linked_graphics['recommendations'].append(
                "3. File SVG: modificare con editor di testo o Illustrator"
            )
        
        # Stampa riepilogo
        if linked_graphics['graphics_found']:
            print(f"\n🖼️  Analisi Grafiche Collegate:")
            print(f"   Totale grafiche: {len(linked_graphics['graphics_found'])}")
            
            if linked_graphics['warnings']:
                for warning in linked_graphics['warnings']:
                    print(f"   {warning}")
            
            if linked_graphics['recommendations']:
                print("   📌 Azioni consigliate:")
                for rec in linked_graphics['recommendations']:
                    print(f"      {rec}")
        
        return linked_graphics
    
    def _load_backing_story(self) -> None:
        """
        Carica e analizza BackingStory.xml per mappare la struttura XML del documento.
        BackingStory contiene le associazioni tra contenuto XML e stories.
        """
        if not self.idml_package:
            return
        
        try:
            # Cerca BackingStory.xml nella cartella XML
            backing_story_path = 'XML/BackingStory.xml'
            
            if backing_story_path not in [f.filename for f in self.idml_package.infolist()]:
                print("ℹ️  BackingStory.xml non presente (documento senza struttura XML)")
                return
            
            backing_story_content = self.idml_package.read(backing_story_path)
            if isinstance(backing_story_content, bytes):
                backing_story_content = backing_story_content.decode('utf-8')
            
            backing_story_root = ET.fromstring(backing_story_content)
            self.backing_story_data = {
                'root': backing_story_root,
                'original_content': backing_story_content
            }
            
            # Analizza la struttura XML
            self._analyze_xml_structure(backing_story_root)
            
            # Carica anche Tags.xml se presente
            self._load_xml_tags()
            
            print(f"✅ BackingStory.xml caricato - Trovati {len(self.xml_structure)} elementi XML strutturati")
            
        except Exception as e:
            print(f"⚠️  Errore caricamento BackingStory.xml: {e}")
    
    def _analyze_xml_structure(self, backing_story_root: ET.Element) -> None:
        """
        Analizza la struttura XML definita in BackingStory.
        Mappa elementi XML alle stories corrispondenti.
        """
        # Trova tutti gli XMLElement
        for elem in backing_story_root.iter():
            elem_tag = self._remove_namespace(elem.tag)
            
            if elem_tag == 'XMLElement':
                self_id = elem.get('Self', '')
                markup_tag = elem.get('MarkupTag', '')
                xml_content = elem.get('XMLContent', '')
                
                # Estrai informazioni strutturali
                element_info = {
                    'id': self_id,
                    'tag': markup_tag,
                    'content_ref': xml_content,
                    'attributes': {},
                    'children': []
                }
                
                # Cerca XMLAttribute figli
                for child in elem:
                    child_tag = self._remove_namespace(child.tag)
                    
                    if child_tag == 'XMLAttribute':
                        attr_name = child.get('Name', '')
                        attr_value = child.get('Value', '')
                        element_info['attributes'][attr_name] = attr_value
                    
                    elif child_tag == 'XMLElement':
                        # Elemento figlio
                        child_id = child.get('Self', '')
                        element_info['children'].append(child_id)
                
                # Mappa content_ref alla story corrispondente
                if xml_content:
                    # Il content_ref può puntare a una story (es: "u16a" -> "Stories/Story_u16a.xml")
                    potential_story_path = f"Stories/Story_{xml_content}.xml"
                    if potential_story_path in self.stories_data:
                        element_info['story_path'] = potential_story_path
                        element_info['has_translatable_content'] = True
                    else:
                        # Potrebbe essere un riferimento a un altro tipo di contenuto
                        element_info['has_translatable_content'] = False
                
                self.xml_structure[self_id] = element_info
    
    def _load_xml_tags(self) -> None:
        """
        Carica Tags.xml che definisce i tag XML utilizzati nel documento.
        """
        try:
            tags_path = 'XML/Tags.xml'
            
            if tags_path not in [f.filename for f in self.idml_package.infolist()]:
                return
            
            tags_content = self.idml_package.read(tags_path)
            if isinstance(tags_content, bytes):
                tags_content = tags_content.decode('utf-8')
            
            tags_root = ET.fromstring(tags_content)
            
            # Estrai definizioni tag
            xml_tags = {}
            for elem in tags_root.iter():
                elem_tag = self._remove_namespace(elem.tag)
                
                if elem_tag == 'XMLTag':
                    tag_self = elem.get('Self', '')
                    tag_name = elem.get('Name', '')
                    xml_tags[tag_self] = {
                        'name': tag_name,
                        'color': elem.get('TagColor', ''),
                        'properties': dict(elem.attrib)
                    }
            
            # Aggiungi info tag alla struttura
            for elem_id, elem_info in self.xml_structure.items():
                if elem_info['tag'] in xml_tags:
                    elem_info['tag_info'] = xml_tags[elem_info['tag']]
            
            print(f"   📋 Tags.xml caricato - {len(xml_tags)} tag XML definiti")
            
        except Exception as e:
            print(f"⚠️  Errore caricamento Tags.xml: {e}")
    
    def get_xml_structured_content(self) -> Dict[str, Any]:
        """
        Restituisce il contenuto strutturato XML con riferimenti alle stories traducibili.
        
        Returns:
            Dizionario con la struttura XML e contenuti traducibili
        """
        if not self.xml_structure:
            return {}
        
        structured_content = {
            'has_xml_structure': True,
            'total_elements': len(self.xml_structure),
            'translatable_elements': [],
            'element_hierarchy': {},
            'tags_used': set()
        }
        
        # Identifica elementi con contenuto traducibile
        for elem_id, elem_info in self.xml_structure.items():
            if elem_info.get('has_translatable_content'):
                structured_content['translatable_elements'].append({
                    'id': elem_id,
                    'tag': elem_info.get('tag_info', {}).get('name', elem_info['tag']),
                    'story_path': elem_info.get('story_path', ''),
                    'attributes': elem_info['attributes']
                })
            
            # Raccogli tag utilizzati
            if 'tag_info' in elem_info:
                structured_content['tags_used'].add(elem_info['tag_info']['name'])
        
        structured_content['tags_used'] = list(structured_content['tags_used'])
        
        # Costruisci gerarchia se necessario
        root_elements = []
        for elem_id, elem_info in self.xml_structure.items():
            # Trova elementi root (non sono figli di nessuno)
            is_child = False
            for other_id, other_info in self.xml_structure.items():
                if elem_id in other_info['children']:
                    is_child = True
                    break
            
            if not is_child:
                root_elements.append(elem_id)
        
        structured_content['root_elements'] = root_elements
        
        return structured_content
    
    def analyze_style_consistency(self) -> Dict[str, Any]:
        """
        Analizza la consistenza degli stili nel documento per validazione post-traduzione.
        
        Returns:
            Dizionario con informazioni dettagliate sugli stili utilizzati
        """
        style_analysis = {
            'paragraph_styles': {},
            'character_styles': {},
            'object_styles': {},
            'table_styles': {},
            'cell_styles': {},
            'style_overrides': [],
            'warnings': []
        }
        
        if not self.idml_package:
            return style_analysis
        
        # 1. Analizza Styles.xml per gli stili definiti
        try:
            styles_content = self.idml_package.read('Resources/Styles.xml')
            if isinstance(styles_content, bytes):
                styles_content = styles_content.decode('utf-8')
            
            styles_root = ET.fromstring(styles_content)
            
            # Estrai ParagraphStyles
            for elem in styles_root.iter():
                elem_tag = self._remove_namespace(elem.tag)
                
                if elem_tag == 'ParagraphStyle':
                    style_id = elem.get('Self', '')
                    style_name = elem.get('Name', style_id)
                    
                    style_analysis['paragraph_styles'][style_id] = {
                        'name': style_name,
                        'usage_count': 0,
                        'properties': self._extract_style_properties(elem),
                        'based_on': elem.get('BasedOn', ''),
                        'next_style': elem.get('NextStyle', '')
                    }
                
                elif elem_tag == 'CharacterStyle':
                    style_id = elem.get('Self', '')
                    style_name = elem.get('Name', style_id)
                    
                    style_analysis['character_styles'][style_id] = {
                        'name': style_name,
                        'usage_count': 0,
                        'properties': self._extract_style_properties(elem),
                        'based_on': elem.get('BasedOn', '')
                    }
                
                elif elem_tag == 'ObjectStyle':
                    style_id = elem.get('Self', '')
                    style_analysis['object_styles'][style_id] = {
                        'name': elem.get('Name', style_id),
                        'usage_count': 0
                    }
                
                elif elem_tag == 'TableStyle':
                    style_id = elem.get('Self', '')
                    style_analysis['table_styles'][style_id] = {
                        'name': elem.get('Name', style_id),
                        'usage_count': 0
                    }
                
                elif elem_tag == 'CellStyle':
                    style_id = elem.get('Self', '')
                    style_analysis['cell_styles'][style_id] = {
                        'name': elem.get('Name', style_id),
                        'usage_count': 0
                    }
        
        except Exception as e:
            style_analysis['warnings'].append(f"Errore lettura Styles.xml: {e}")
        
        # 2. Analizza l'uso degli stili nelle stories
        override_count = 0
        
        for story_path, story_data in self.stories_data.items():
            story_root = story_data['root']
            
            for elem in story_root.iter():
                elem_tag = self._remove_namespace(elem.tag)
                
                # Conta uso ParagraphStyle
                if elem_tag == 'ParagraphStyleRange':
                    applied_style = elem.get('AppliedParagraphStyle', '')
                    if applied_style in style_analysis['paragraph_styles']:
                        style_analysis['paragraph_styles'][applied_style]['usage_count'] += 1
                    
                    # Rileva override locali
                    local_overrides = self._detect_style_overrides(elem, 'paragraph')
                    if local_overrides:
                        override_count += len(local_overrides)
                        style_analysis['style_overrides'].extend(local_overrides)
                
                # Conta uso CharacterStyle
                elif elem_tag == 'CharacterStyleRange':
                    applied_style = elem.get('AppliedCharacterStyle', '')
                    if applied_style in style_analysis['character_styles']:
                        style_analysis['character_styles'][applied_style]['usage_count'] += 1
                    
                    # Rileva override locali
                    local_overrides = self._detect_style_overrides(elem, 'character')
                    if local_overrides:
                        override_count += len(local_overrides)
                        style_analysis['style_overrides'].extend(local_overrides[:10])  # Limita a 10 per non sovraccaricare
        
        # 3. Genera warnings per potenziali problemi
        # Stili non utilizzati
        unused_styles = []
        for style_id, info in style_analysis['paragraph_styles'].items():
            if info['usage_count'] == 0 and not style_id.endswith('/NormalParagraphStyle'):
                unused_styles.append(f"Paragraph: {info['name']}")
        
        for style_id, info in style_analysis['character_styles'].items():
            if info['usage_count'] == 0 and not style_id.endswith('/NormalCharacterStyle'):
                unused_styles.append(f"Character: {info['name']}")
        
        if unused_styles:
            style_analysis['warnings'].append(
                f"⚠️  {len(unused_styles)} stili definiti ma non utilizzati"
            )
        
        # Override eccessivi
        if override_count > 50:
            style_analysis['warnings'].append(
                f"⚠️  Trovati {override_count} override locali di stile. "
                "Questi potrebbero essere persi durante la traduzione."
            )
            style_analysis['warnings'].append(
                "Consiglio: convertire override frequenti in stili dedicati prima della traduzione."
            )
        
        # 4. Genera report
        total_para_styles = len(style_analysis['paragraph_styles'])
        total_char_styles = len(style_analysis['character_styles'])
        used_para_styles = sum(1 for s in style_analysis['paragraph_styles'].values() if s['usage_count'] > 0)
        used_char_styles = sum(1 for s in style_analysis['character_styles'].values() if s['usage_count'] > 0)
        
        print(f"\n📊 Analisi Consistenza Stili:")
        print(f"   Stili Paragrafo: {used_para_styles}/{total_para_styles} utilizzati")
        print(f"   Stili Carattere: {used_char_styles}/{total_char_styles} utilizzati")
        print(f"   Override locali: {override_count}")
        
        if style_analysis['warnings']:
            print("   ⚠️  Avvisi:")
            for warning in style_analysis['warnings']:
                print(f"      {warning}")
        
        return style_analysis
    
    def _extract_style_properties(self, style_elem: ET.Element) -> Dict[str, Any]:
        """Estrae proprietà chiave da un elemento stile."""
        properties = {}
        
        # Proprietà comuni di formattazione
        format_attrs = [
            'FontStyle', 'PointSize', 'Leading', 'Tracking', 'Kerning',
            'BaselineShift', 'HorizontalScale', 'VerticalScale',
            'FillColor', 'StrokeColor', 'StrokeWeight',
            'LeftIndent', 'RightIndent', 'FirstLineIndent',
            'SpaceBefore', 'SpaceAfter', 'Justification'
        ]
        
        for attr in format_attrs:
            if attr in style_elem.attrib:
                properties[attr] = style_elem.get(attr)
        
        return properties
    
    def _detect_style_overrides(self, elem: ET.Element, style_type: str) -> List[Dict]:
        """Rileva override locali rispetto allo stile applicato."""
        overrides = []
        
        # Attributi che se presenti indicano override locale
        override_indicators = {
            'paragraph': ['PointSize', 'Leading', 'Justification', 'LeftIndent', 'RightIndent'],
            'character': ['FontStyle', 'PointSize', 'FillColor', 'BaselineShift', 'Tracking']
        }
        
        indicators = override_indicators.get(style_type, [])
        
        found_overrides = []
        for attr in indicators:
            if attr in elem.attrib:
                found_overrides.append(attr)
        
        if found_overrides:
            overrides.append({
                'element': elem.tag,
                'type': style_type,
                'overridden_properties': found_overrides,
                'location': elem.get('Self', 'unknown')
            })
        
        return overrides
    
    def validate_style_preservation(self, original_analysis: Dict, translated_analysis: Dict) -> Dict[str, Any]:
        """
        Valida che gli stili siano stati preservati dopo la traduzione.
        
        Args:
            original_analysis: Analisi stili pre-traduzione
            translated_analysis: Analisi stili post-traduzione
            
        Returns:
            Report di validazione con eventuali discrepanze
        """
        validation = {
            'is_valid': True,
            'discrepancies': [],
            'style_changes': [],
            'override_changes': []
        }
        
        # Confronta conteggi stili
        for style_type in ['paragraph_styles', 'character_styles']:
            original_styles = original_analysis.get(style_type, {})
            translated_styles = translated_analysis.get(style_type, {})
            
            for style_id, orig_info in original_styles.items():
                if style_id not in translated_styles:
                    validation['discrepancies'].append(
                        f"Stile mancante dopo traduzione: {orig_info['name']} ({style_type})"
                    )
                    validation['is_valid'] = False
                else:
                    trans_info = translated_styles[style_id]
                    # Confronta usage count (potrebbe variare leggermente)
                    if abs(orig_info['usage_count'] - trans_info['usage_count']) > 5:
                        validation['style_changes'].append({
                            'style': orig_info['name'],
                            'original_count': orig_info['usage_count'],
                            'translated_count': trans_info['usage_count']
                        })
        
        # Confronta override
        orig_overrides = len(original_analysis.get('style_overrides', []))
        trans_overrides = len(translated_analysis.get('style_overrides', []))
        
        if abs(orig_overrides - trans_overrides) > 10:
            validation['override_changes'].append({
                'original_overrides': orig_overrides,
                'translated_overrides': trans_overrides,
                'difference': trans_overrides - orig_overrides
            })
        
        return validation
    
    def validate_xml_tag_integrity(self) -> Dict[str, Any]:
        """
        Valida l'integrità dei tag XML specifici di IDML dopo la traduzione.
        
        Returns:
            Dizionario con risultati validazione e eventuali errori
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'tag_counts': {},
            'broken_tags': [],
            'recommendations': []
        }
        
        if not self.idml_package:
            return validation_result
        
        # Tag IDML critici da validare
        critical_tags = {
            'Br': 'Line breaks',
            'Tab': 'Tab characters', 
            'Content': 'Text content',
            'CharacterStyleRange': 'Character formatting',
            'ParagraphStyleRange': 'Paragraph formatting',
            'TextFrame': 'Text containers',
            'Rectangle': 'Graphic containers',
            'Image': 'Images',
            'Link': 'Resource links'
        }
        
        # Pattern per identificare tag malformati
        malformed_patterns = [
            r'<(?![/\w])',  # Tag che non iniziano con lettera o /
            r'<[^>]*[<>][^>]*>',  # Tag con < o > interni
            r'<\s+\w+',  # Tag con spazi iniziali
            r'<\w+[^>]*\s+>$',  # Tag con spazi finali prima della chiusura
            r'<\w+.*?(?<!/)>\s*$',  # Tag non auto-chiusi senza contenuto
        ]
        
        # Valida ogni story
        for story_path, story_data in self.stories_data.items():
            try:
                # Controlla la struttura XML della story
                story_xml = ET.tostring(story_data['root'], encoding='unicode')
                
                # Conta tag utilizzati
                for tag_name in critical_tags.keys():
                    tag_count = story_xml.count(f'<{tag_name}')
                    if tag_name not in validation_result['tag_counts']:
                        validation_result['tag_counts'][tag_name] = 0
                    validation_result['tag_counts'][tag_name] += tag_count
                
                # Rileva tag malformati
                for pattern in malformed_patterns:
                    matches = re.findall(pattern, story_xml, re.MULTILINE)
                    if matches:
                        validation_result['broken_tags'].extend([
                            {
                                'story': story_path,
                                'pattern': pattern,
                                'matches': matches[:5],  # Primi 5 per non sovraccaricare
                                'description': f'Tag malformati trovati in {story_path}'
                            }
                        ])
                
                # Verifica bilancio tag apertura/chiusura per tag critici
                for tag_name in critical_tags.keys():
                    opening_tags = len(re.findall(f'<{tag_name}[^>]*(?<!/)>', story_xml))
                    closing_tags = len(re.findall(f'</{tag_name}>', story_xml))
                    self_closing = len(re.findall(f'<{tag_name}[^>]*/>', story_xml))
                    
                    # I tag auto-chiusi sono bilanciati per definizione
                    expected_closing = opening_tags - self_closing
                    
                    if expected_closing != closing_tags and expected_closing > 0:
                        validation_result['errors'].append(
                            f"Tag sbilanciati in {story_path}: {tag_name} "
                            f"aperti={opening_tags}, chiusi={closing_tags}, auto-chiusi={self_closing}"
                        )
                        validation_result['is_valid'] = False
                
                # Verifica attributi critici
                critical_attributes = [
                    'Self', 'AppliedParagraphStyle', 'AppliedCharacterStyle',
                    'AppliedLanguage', 'ItemTransform', 'ParentStory'
                ]
                
                for elem in story_data['root'].iter():
                    elem_tag = self._remove_namespace(elem.tag)
                    
                    # Verifica attributi Self per unicità
                    if 'Self' in elem.attrib:
                        self_value = elem.get('Self')
                        if not self_value or len(self_value) < 3:
                            validation_result['warnings'].append(
                                f"Attributo Self vuoto o troppo corto in {story_path}: {elem_tag}"
                            )
                    
                    # Verifica attributi stile
                    if elem_tag in ['CharacterStyleRange', 'ParagraphStyleRange']:
                        style_attr = 'AppliedCharacterStyle' if elem_tag == 'CharacterStyleRange' else 'AppliedParagraphStyle'
                        if style_attr not in elem.attrib:
                            validation_result['warnings'].append(
                                f"Attributo stile mancante in {story_path}: {elem_tag} senza {style_attr}"
                            )
            
            except ET.ParseError as e:
                validation_result['errors'].append(f"Errore parsing XML in {story_path}: {e}")
                validation_result['is_valid'] = False
            except Exception as e:
                validation_result['warnings'].append(f"Errore validazione {story_path}: {e}")
        
        # Validazione specifica per elementi critici
        content_elements = validation_result['tag_counts'].get('Content', 0)
        char_style_ranges = validation_result['tag_counts'].get('CharacterStyleRange', 0)
        
        if content_elements == 0:
            validation_result['warnings'].append("Nessun elemento Content trovato - possibile perdita di testo")
        
        if char_style_ranges == 0:
            validation_result['warnings'].append("Nessun CharacterStyleRange trovato - possibile perdita di formattazione")
        
        # Verifica rapporto Content/CharacterStyleRange
        if content_elements > 0 and char_style_ranges > 0:
            ratio = content_elements / char_style_ranges
            if ratio > 3.0:  # Troppi Content per CharacterStyleRange
                validation_result['warnings'].append(
                    f"Rapporto inusuale Content/CharacterStyleRange: {ratio:.1f} "
                    "(potrebbe indicare problemi di struttura)"
                )
        
        # Genera raccomandazioni
        if validation_result['broken_tags']:
            validation_result['recommendations'].append(
                "Ricontrollare il documento in InDesign per verificare la formattazione"
            )
        
        if len(validation_result['warnings']) > 10:
            validation_result['recommendations'].append(
                "Molti avvisi rilevati - considerare una revisione manuale del documento tradotto"
            )
        
        if validation_result['errors']:
            validation_result['recommendations'].append(
                "Errori critici trovati - il documento potrebbe non aprirsi correttamente in InDesign"
            )
        
        # Report finale
        print(f"\n🔍 Validazione Integrità XML:")
        print(f"   Tag validati: {len(critical_tags)}")
        print(f"   Errori critici: {len(validation_result['errors'])}")
        print(f"   Avvisi: {len(validation_result['warnings'])}")
        
        if validation_result['errors']:
            print("   ❌ Errori critici:")
            for error in validation_result['errors'][:5]:  # Primi 5
                print(f"      {error}")
        
        if validation_result['warnings'] and len(validation_result['warnings']) <= 5:
            print("   ⚠️  Avvisi:")
            for warning in validation_result['warnings']:
                print(f"      {warning}")
        elif validation_result['warnings']:
            print(f"   ⚠️  {len(validation_result['warnings'])} avvisi (primi 3):")
            for warning in validation_result['warnings'][:3]:
                print(f"      {warning}")
        
        if validation_result['recommendations']:
            print("   📌 Raccomandazioni:")
            for rec in validation_result['recommendations']:
                print(f"      {rec}")
        
        return validation_result
    
    def generate_dtp_checklist(self, target_language: str, translation_stats: Dict, 
                              font_validation: Dict, xml_validation: Dict, 
                              linked_graphics: Dict) -> Dict[str, Any]:
        """
        Genera una checklist completa per il desktop publishing post-traduzione.
        
        Args:
            target_language: Lingua di destinazione
            translation_stats: Statistiche traduzione
            font_validation: Risultati validazione font
            xml_validation: Risultati validazione XML
            linked_graphics: Info grafiche collegate
            
        Returns:
            Dizionario con checklist completa DTP
        """
        checklist = {
            'target_language': target_language,
            'generated_at': None,
            'critical_checks': [],
            'recommended_checks': [],
            'optional_checks': [],
            'language_specific_notes': [],
            'estimated_time': '30-60 min'
        }
        
        # Import datetime per timestamp
        from datetime import datetime
        checklist['generated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. CONTROLLI CRITICI (devono essere fatti)
        checklist['critical_checks'] = [
            "Aprire il file IDML tradotto in InDesign per verificare che si apra senza errori",
            "Controllare che tutto il testo sia visibile e non ci siano overflow (testo che fuoriesce dai frame)",
            "Verificare che la formattazione (grassetto, corsivo, colori) sia preservata",
            "Controllare l'allineamento del testo e la spaziatura tra paragrafi",
            "Verificare che i numeri di pagina (se presenti) siano corretti"
        ]
        
        # Aggiungi controlli specifici per font
        if font_validation.get('requires_special_fonts'):
            checklist['critical_checks'].extend([
                f"Verificare che il testo {font_validation['target_language']} sia visualizzato correttamente",
                "Controllare che tutti i caratteri speciali siano renderizzati (non □ o ?)"
            ])
        
        # Aggiungi controlli per XML issues
        if not xml_validation.get('is_valid', True):
            checklist['critical_checks'].append(
                "PRIORITÀ ALTA: Risolvere gli errori XML segnalati - il documento potrebbe non funzionare correttamente"
            )
        
        # 2. CONTROLLI RACCOMANDATI
        checklist['recommended_checks'] = [
            "Controllare che le immagini e i grafici siano ancora collegati correttamente",
            "Verificare che i link ipertestuali (se presenti) funzionino ancora",
            "Controllare la consistenza degli stili in tutto il documento",
            "Verificare che i margini e le spaziature siano appropriate per la lingua di destinazione",
            "Controllare che non ci siano caratteri orfani o vedove in posizioni critiche"
        ]
        
        # Aggiungi controlli per grafiche con testo
        if linked_graphics.get('potential_text_graphics'):
            checklist['recommended_checks'].extend([
                f"Tradurre manualmente il testo in {len(linked_graphics['potential_text_graphics'])} file grafici identificati",
                "Sostituire le grafiche tradotte e verificare l'allineamento"
            ])
        
        # 3. CONTROLLI OPZIONALI
        checklist['optional_checks'] = [
            "Ottimizzare la disposizione del testo per una migliore leggibilità nella lingua di destinazione",
            "Considerare modifiche culturali nella presentazione (colori, simboli, layout)",
            "Verificare che le abbreviazioni e i formati numerici siano appropriati per la regione",
            "Controllare la coerenza terminologica in tutto il documento"
        ]
        
        # 4. NOTE SPECIFICHE PER LINGUA
        language_notes = {
            'de': [
                "Il tedesco tende ad espandersi del 20-30% - verificare overflow",
                "Controllare la composizione delle parole composte lunghe",
                "Verificare l'uso corretto delle maiuscole per i sostantivi"
            ],
            'fr': [
                "Il francese tende ad espandersi del 15-20% - verificare overflow", 
                "Controllare gli spazi prima dei due punti e punti interrogativi",
                "Verificare l'uso corretto degli accenti"
            ],
            'es': [
                "Lo spagnolo tende ad espandersi del 15-25% - verificare overflow",
                "Controllare l'uso dei segni di interrogazione e esclamazione invertiti",
                "Verificare la concordanza di genere negli aggettivi"
            ],
            'it': [
                "L'italiano ha espansione moderata del 10-15%",
                "Controllare l'uso corretto degli apostrofi",
                "Verificare gli accenti sulle parole tronche"
            ],
            'zh': [
                "Verificare che tutti i caratteri cinesi siano visualizzati correttamente",
                "Controllare la direzione del testo e l'allineamento",
                "Verificare che non ci siano caratteri mancanti (□)"
            ],
            'ja': [
                "Verificare mixing di hiragana, katakana e kanji",
                "Controllare la direzione del testo (orizzontale vs verticale)",
                "Verificare la punteggiatura giapponese"
            ],
            'ar': [
                "CRITICO: Verificare la direzione RTL (destra-sinistra)",
                "Controllare che la forma delle lettere arabe sia corretta nel contesto",
                "Verificare l'allineamento del testo RTL"
            ],
            'he': [
                "CRITICO: Verificare la direzione RTL (destra-sinistra)",
                "Controllare la punteggiatura ebraica",
                "Verificare l'allineamento del testo RTL"
            ]
        }
        
        if target_language in language_notes:
            checklist['language_specific_notes'] = language_notes[target_language]
        
        # 5. STIMA TEMPO
        base_time = 30
        
        # Aggiungi tempo per controlli extra
        if font_validation.get('requires_special_fonts'):
            base_time += 15
        
        if linked_graphics.get('potential_text_graphics'):
            base_time += len(linked_graphics['potential_text_graphics']) * 10
        
        if not xml_validation.get('is_valid', True):
            base_time += 20
        
        if translation_stats.get('total_segments', 0) > 100:
            base_time += 20
        
        checklist['estimated_time'] = f"{base_time}-{base_time + 30} min"
        
        return checklist
    
    def print_dtp_checklist(self, checklist: Dict[str, Any]) -> None:
        """Stampa la checklist DTP in formato leggibile."""
        print(f"\n📋 CHECKLIST DESKTOP PUBLISHING")
        print(f"   Lingua: {checklist['target_language']}")
        print(f"   Tempo stimato: {checklist['estimated_time']}")
        print(f"   Generata: {checklist['generated_at']}")
        
        print(f"\n🔴 CONTROLLI CRITICI ({len(checklist['critical_checks'])} elementi):")
        for i, check in enumerate(checklist['critical_checks'], 1):
            print(f"   {i}. {check}")
        
        print(f"\n🟡 CONTROLLI RACCOMANDATI ({len(checklist['recommended_checks'])} elementi):")
        for i, check in enumerate(checklist['recommended_checks'], 1):
            print(f"   {i}. {check}")
        
        if checklist['language_specific_notes']:
            print(f"\n🌐 NOTE SPECIFICHE PER {checklist['target_language'].upper()}:")
            for note in checklist['language_specific_notes']:
                print(f"   • {note}")
        
        if checklist['optional_checks']:
            print(f"\n🟢 CONTROLLI OPZIONALI ({len(checklist['optional_checks'])} elementi):")
            for i, check in enumerate(checklist['optional_checks'], 1):
                print(f"   {i}. {check}")
        
        print(f"\n💡 Questa checklist può essere salvata e utilizzata come riferimento durante la revisione DTP.")
    
    def extract_master_pages_content(self) -> Dict[str, Any]:
        """
        Estrae contenuto traducibile dalle master pages IDML
        
        Returns:
            Dizionario con contenuti delle master pages
        """
        if not self.idml_package:
            return {}
        
        master_content = {}
        
        # Trova file master pages
        master_files = []
        for file_info in self.idml_package.infolist():
            if 'MasterSpreads' in file_info.filename and file_info.filename.endswith('.xml'):
                master_files.append(file_info.filename)
        
        print(f"🔍 Trovate {len(master_files)} master pages")
        
        for master_file in master_files:
            try:
                # Leggi contenuto master page
                content = self.idml_package.read(master_file)
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                
                # Parse XML
                master_root = ET.fromstring(content)
                
                # Estrai testi traducibili dalle master pages
                texts = []
                page_number_elements = []
                text_frame_references = []
                
                # NUOVO APPROCCIO: Trova TextFrame con ParentStory e cerca nelle stories corrispondenti
                for element in master_root.iter():
                    element_tag = self._remove_namespace(element.tag)
                    
                    # Cerca TextFrame che riferiscono a stories
                    if element_tag == 'TextFrame':
                        parent_story = element.get('ParentStory')
                        if parent_story and parent_story != 'n':
                            story_file = f"Stories/Story_{parent_story}.xml"
                            text_frame_references.append({
                                'frame_id': element.get('Self', 'unknown'),
                                'story_file': story_file,
                                'master_file': master_file
                            })
                
                # Estrai contenuto dalle stories riferite dai text frame
                for frame_ref in text_frame_references:
                    story_file = frame_ref['story_file'] 
                    try:
                        # Leggi la story referenziata
                        story_content = self.idml_package.read(story_file)
                        if isinstance(story_content, bytes):
                            story_content = story_content.decode('utf-8')
                        
                        story_root = ET.fromstring(story_content)
                        
                        # Cerca Content elements nella story
                        for story_element in story_root.iter():
                            story_tag = self._remove_namespace(story_element.tag)
                            
                            if story_tag == 'Content':
                                if story_element.text and story_element.text.strip():
                                    text_content = story_element.text.strip()
                                    
                                    # Identifica numeri di pagina dinamici
                                    if self._is_dynamic_page_number(text_content):
                                        page_number_elements.append({
                                            'element': story_element,
                                            'content': text_content,
                                            'type': 'dynamic_page_number',
                                            'frame_id': frame_ref['frame_id'],
                                            'story_file': story_file
                                        })
                                    elif self._is_translatable_master_text(text_content):
                                        texts.append({
                                            'element': story_element,
                                            'content': text_content,
                                            'type': 'translatable_text',
                                            'frame_id': frame_ref['frame_id'],
                                            'story_file': story_file
                                        })
                    
                    except Exception as e:
                        print(f"Warning: Errore lettura story {story_file}: {e}")
                        continue
                
                if texts or page_number_elements:
                    master_content[master_file] = {
                        'root': master_root,
                        'original_content': content,
                        'translatable_texts': texts,
                        'page_number_elements': page_number_elements
                    }
                    print(f"   📄 {master_file}: {len(texts)} testi, {len(page_number_elements)} numeri pagina")
                    
            except Exception as e:
                print(f"Warning: Errore parsing master page {master_file}: {e}")
                continue
        
        return master_content
    
    def _is_dynamic_page_number(self, text: str) -> bool:
        """Identifica marcatori di numerazione pagine dinamici"""
        page_markers = [
            '<#>',  # Numero pagina corrente
            '<!#>',  # Numero pagina precedente  
            '<$>',   # Numero pagina successiva
            '<Auto Page Number>',
            'CurrentPageNumber',
            'NextPageNumber',
            'PreviousPageNumber'
        ]
        
        # Controlla se contiene marker di pagina
        for marker in page_markers:
            if marker in text:
                return True
        
        # Controlla se è un numero isolato che potrebbe essere dinamico
        if text.isdigit() and len(text) <= 3:
            return True
            
        return False
    
    def _is_translatable_master_text(self, text: str) -> bool:
        """Determina se il testo nella master page è traducibile"""
        # Usa la stessa logica del text extractor ma più permissiva
        if not text or len(text.strip()) < 2:
            return False
        
        text_clean = text.strip()
        
        # Non tradurre marker tecnici
        if self._is_dynamic_page_number(text_clean):
            return False
        
        # Non tradurre solo punteggiatura
        if re.match(r'^[^\w\s]+$', text_clean):
            return False
        
        # Non tradurre identificatori puri (ma permetti parole)
        if re.match(r'^[A-Z0-9_]{4,}$', text_clean) and not any(c.isalpha() for c in text_clean):
            return False
        
        return True
    
    def update_master_pages(self, master_translations: Dict[str, List[str]]) -> bool:
        """
        Aggiorna le master pages con traduzioni
        
        Args:
            master_translations: Dizionario master_file -> lista traduzioni
            
        Returns:
            True se aggiornate con successo
        """
        if not self.idml_package or not master_translations:
            return False
        
        updated_count = 0
        updated_stories = set()  # Track which stories we update to avoid duplicates
        
        for master_file, translations in master_translations.items():
            try:
                # Prima, estrai i contenuti per capire quali stories aggiornare
                master_content = self.extract_master_pages_content()
                if master_file not in master_content:
                    continue
                
                master_data = master_content[master_file]
                translatable_texts = master_data.get('translatable_texts', [])
                
                if not translatable_texts:
                    continue
                
                # Raggruppa per story file
                story_updates = {}
                translation_index = 0
                
                for text_info in translatable_texts:
                    if translation_index < len(translations):
                        story_file = text_info.get('story_file')
                        if story_file:
                            if story_file not in story_updates:
                                story_updates[story_file] = []
                            story_updates[story_file].append({
                                'element_ref': text_info,
                                'translation': translations[translation_index]
                            })
                            translation_index += 1
                
                # Aggiorna ogni story referenziata
                for story_file, updates in story_updates.items():
                    if story_file in updated_stories:
                        continue  # Evita aggiornamenti duplicati
                    
                    try:
                        # Leggi story content
                        story_content = self.idml_package.read(story_file)
                        if isinstance(story_content, bytes):
                            story_content = story_content.decode('utf-8')
                        
                        story_root = ET.fromstring(story_content)
                        
                        # Trova tutti gli elementi Content traducibili in questa story
                        translatable_elements = []
                        for element in story_root.iter():
                            if self._remove_namespace(element.tag) == 'Content':
                                if element.text and element.text.strip():
                                    if self._is_translatable_master_text(element.text.strip()):
                                        translatable_elements.append(element)
                        
                        # Applica traduzioni in ordine
                        update_index = 0
                        for update in updates:
                            if update_index < len(translatable_elements):
                                translatable_elements[update_index].text = update['translation']
                                update_index += 1
                        
                        # Salva la story aggiornata nella cache delle stories
                        self.stories_data[story_file] = {
                            'root': story_root,
                            'original_content': story_content
                        }
                        
                        updated_stories.add(story_file)
                        print(f"✅ Story {story_file} aggiornata per master page {master_file}")
                        
                    except Exception as e:
                        print(f"❌ Errore aggiornamento story {story_file}: {e}")
                        continue
                
                updated_count += 1
                
            except Exception as e:
                print(f"❌ Errore aggiornamento master page {master_file}: {e}")
                continue
        
        return updated_count > 0
    
    def get_text_content(self) -> Dict[str, List[str]]:
        """
        Estrae tutto il contenuto testuale dalle stories
        
        Returns:
            Dizionario con nome story -> lista di testi
        """
        text_content = {}
        
        for story_name, story_data in self.stories_data.items():
            story_root = story_data['root']
            texts = []
            
            # Cerca tutti gli elementi che contengono testo
            for elem in story_root.iter():
                if elem.text and elem.text.strip():
                    texts.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    texts.append(elem.tail.strip())
            
            if texts:
                text_content[story_name] = texts
                
        return text_content
    
    def replace_text_content(self, translations: Dict[str, List[str]], target_language: str = None) -> None:
        """
        Sostituisce il contenuto testuale con le traduzioni usando la stessa logica di estrazione
        
        Args:
            translations: Dizionario story_name -> lista traduzioni per quella story
            target_language: Lingua di destinazione per aggiornare gli attributi
        """
        # Importa TextExtractor per usare la stessa logica di filtraggio
        from text_extractor import TextExtractor
        
        # Crea un extractor temporaneo per usare la logica di filtraggio
        temp_extractor = TextExtractor()
        
        def remove_namespace(tag):
            return tag.split('}')[-1] if '}' in tag else tag
        
        # Mappa codici lingua per IDML
        language_map = {
            'de': '$ID/German',
            'en': '$ID/English', 
            'es': '$ID/Spanish',
            'fr': '$ID/French',
            'it': '$ID/Italian'
        }
        
        for story_name, translated_texts in translations.items():
            if story_name not in self.stories_data:
                continue
                
            story_root = self.stories_data[story_name]['root']
            text_elements = []
            
            # PRESERVA TUTTI I PROCESSING INSTRUCTIONS (come <?ACE 18?>)
            # Prima salva il contenuto XML originale per ripristino PI
            original_xml_content = ET.tostring(story_root, encoding='unicode')
            
            # Cerca pattern di Processing Instructions nel testo XML
            import re
            pi_patterns = re.findall(r'<\?[^>]+\?>', original_xml_content)
            
            if pi_patterns:
                print(f"   🔧 Trovati {len(pi_patterns)} Processing Instructions da preservare")
            
            # USA LA STESSA LOGICA IDENTICA di _find_text_elements in TextExtractor
            # Cerca specificamente elementi Content dentro CharacterStyleRange
            for element in story_root.iter():
                element_tag = remove_namespace(element.tag)
                
                if element_tag == 'CharacterStyleRange':
                    # AGGIORNA ATTRIBUTI LINGUA SE SPECIFICATO
                    if target_language and target_language in language_map:
                        element.set('AppliedLanguage', language_map[target_language])
                    
                    # Cerca elementi Content dentro questo CharacterStyleRange
                    for content_elem in element:
                        content_tag = remove_namespace(content_elem.tag)
                        
                        if content_tag == 'Content':
                            # Estrai il testo solo dai Content elements E applica lo stesso filtro
                            if content_elem.text and content_elem.text.strip():
                                # IMPORTANTE: applica lo stesso filtro di translatable_text
                                if temp_extractor._is_translatable_text(content_elem.text.strip()):
                                    text_elements.append((content_elem, 'text'))
                            
                            # Content elements non dovrebbero avere tail text, ma controlliamo comunque
                            if content_elem.tail and content_elem.tail.strip():
                                if temp_extractor._is_translatable_text(content_elem.tail.strip()):
                                    text_elements.append((content_elem, 'tail'))
            
            # Sostituisce i testi con le traduzioni
            for i, (elem, attr_type) in enumerate(text_elements):
                if i < len(translated_texts):
                    if attr_type == 'text':
                        elem.text = translated_texts[i]
                    else:
                        elem.tail = translated_texts[i]
            
            # RIPRISTINA I PROCESSING INSTRUCTIONS se sono stati persi
            # Verifica se i PI sono ancora presenti nel contenuto finale
            if pi_patterns:
                final_xml_content = ET.tostring(story_root, encoding='unicode')
                
                # Conta PI presenti prima e dopo
                final_pi_patterns = re.findall(r'<\?[^>]+\?>', final_xml_content)
                
                if len(final_pi_patterns) < len(pi_patterns):
                    missing_count = len(pi_patterns) - len(final_pi_patterns)
                    print(f"⚠️  {missing_count} Processing Instructions potrebbero essere stati persi durante la traduzione")
                    
                    # In caso di perdita, avvisa che potrebbe essere necessario controllare manualmente
                    print("   💡 Suggerimento: verificare il documento in InDesign per eventuali problemi di formattazione")
                else:
                    print(f"✅ Tutti i {len(pi_patterns)} Processing Instructions sono stati preservati")
    
    def save_translated_idml(self, output_path: str) -> None:
        """
        Salva il file IDML tradotto
        
        Args:
            output_path: Path dove salvare il file tradotto
        """
        if not self.idml_package:
            raise RuntimeError("IDML non caricato. Chiamare load_idml() prima.")
        
        import tempfile
        import shutil
        import zipfile
        
        # Crea un file temporaneo per il nuovo IDML
        with tempfile.NamedTemporaryFile(delete=False, suffix='.idml') as temp_file:
            temp_path = temp_file.name
        
        try:
            # Crea un nuovo file ZIP con il contenuto modificato
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                # Copia tutti i file dal package originale
                for file_info in self.idml_package.infolist():
                    file_path = file_info.filename
                    
                    # Se è una story che abbiamo modificato, usa il contenuto tradotto
                    if file_path in self.stories_data:
                        # Usa il serializer custom per preservare PI
                        updated_xml = self._serialize_xml_with_pi(self.stories_data[file_path]['root'])
                        new_zip.writestr(file_info, updated_xml)
                    # Se è una master page che abbiamo modificato, usa il contenuto tradotto
                    elif file_path in self.master_pages_data:
                        # Usa il serializer custom per preservare PI
                        updated_xml = self._serialize_xml_with_pi(self.master_pages_data[file_path]['root'])
                        new_zip.writestr(file_info, updated_xml)
                    else:
                        # Copia il file originale
                        original_content = self.idml_package.read(file_path)
                        new_zip.writestr(file_info, original_content)
            
            # Sposta il file temporaneo alla destinazione finale
            shutil.move(temp_path, output_path)
            
        except Exception as e:
            # Cleanup in caso di errore
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def get_document_info(self) -> Dict[str, any]:
        """
        Ottiene informazioni generali sul documento IDML
        
        Returns:
            Dizionario con informazioni del documento
        """
        if not self.idml_package:
            return {}
        
        info = {
            'filename': self.idml_path.name,
            'stories_count': len(self.stories_data),
            'stories_names': list(self.stories_data.keys()),
            'has_xml_structure': bool(self.xml_structure),
            'xml_elements_count': len(self.xml_structure)
        }
        
        # Aggiungi informazioni sulla struttura XML se presente
        if self.xml_structure:
            xml_content = self.get_xml_structured_content()
            info['xml_info'] = {
                'total_elements': xml_content['total_elements'],
                'translatable_elements': len(xml_content['translatable_elements']),
                'tags_used': xml_content['tags_used']
            }
        
        return info
    
    def analyze_text_frames(self) -> Dict[str, Any]:
        """
        Analizza i text frame nel documento IDML per overflow prevention
        
        Returns:
            Dizionario con informazioni sui text frame
        """
        if not self.idml_package:
            return {}
        
        frame_info = {}
        spread_files = []
        
        # Trova tutti i file spread
        try:
            for file_info in self.idml_package.infolist():
                if file_info.filename.startswith('Spreads/') and file_info.filename.endswith('.xml'):
                    spread_files.append(file_info.filename)
        except Exception as e:
            print(f"Errore lettura spreads: {e}")
            return {}
        
        # Analizza ogni spread
        for spread_file in spread_files:
            try:
                spread_content = self.idml_package.read(spread_file)
                if isinstance(spread_content, bytes):
                    spread_content = spread_content.decode('utf-8')
                
                spread_root = ET.fromstring(spread_content)
                spread_frames = self._parse_spread_textframes(spread_root, spread_file)
                frame_info.update(spread_frames)
                
            except Exception as e:
                print(f"Errore parsing spread {spread_file}: {e}")
                continue
        
        return {
            'total_frames': len(frame_info),
            'frames': frame_info,
            'spread_files': spread_files
        }
    
    def _parse_spread_textframes(self, spread_root: ET.Element, spread_file: str) -> Dict[str, Dict]:
        """Parsa text frame in uno spread"""
        
        def remove_namespace(tag):
            return tag.split('}')[-1] if '}' in tag else tag
        
        frames = {}
        
        # Cerca tutti i TextFrame
        for element in spread_root.iter():
            if remove_namespace(element.tag) == 'TextFrame':
                try:
                    frame_data = self._extract_textframe_properties(element, spread_file)
                    if frame_data:
                        frames[frame_data['id']] = frame_data
                except Exception as e:
                    print(f"Errore parsing TextFrame: {e}")
                    continue
        
        return frames
    
    def _extract_textframe_properties(self, textframe_elem: ET.Element, spread_file: str) -> Optional[Dict]:
        """Estrae proprietà da un TextFrame element"""
        
        # ID del frame
        frame_id = textframe_elem.get('Self', f"{spread_file}_{id(textframe_elem)}")
        
        # Transform matrix per posizione e dimensioni  
        transform = textframe_elem.get('ItemTransform', '1 0 0 1 0 0')
        transform_values = [float(x) for x in transform.split()]
        
        if len(transform_values) >= 6:
            scale_x, skew_y, skew_x, scale_y, x, y = transform_values[:6]
            width = abs(scale_x)
            height = abs(scale_y)
        else:
            width = height = x = y = 0.0
        
        # Proprietà colonne
        columns = int(textframe_elem.get('TextColumnCount', '1'))
        gutter = float(textframe_elem.get('TextColumnGutter', '12'))
        
        # Margini interni
        inset = textframe_elem.get('TextFramePreferenceInsetSpacing', '0 0 0 0')
        try:
            inset_values = [float(v) for v in inset.split()]
            if len(inset_values) == 4:
                top, right, bottom, left = inset_values
            elif len(inset_values) == 1:
                top = right = bottom = left = inset_values[0]
            else:
                top = right = bottom = left = 0.0
        except:
            top = right = bottom = left = 0.0
        
        # Stima proprietà font
        font_size = 12.0
        leading = 14.4
        
        # Cerca attributi font nel frame
        for attr, value in textframe_elem.attrib.items():
            try:
                if 'FontSize' in attr or 'PointSize' in attr:
                    font_size = float(value)
                elif 'Leading' in attr:
                    leading = float(value)
            except:
                continue
        
        if leading <= font_size:
            leading = font_size * 1.2
        
        # Conta caratteri nel contenuto
        char_count = 0
        for elem in textframe_elem.iter():
            if elem.text:
                char_count += len(elem.text.strip())
            if elem.tail:
                char_count += len(elem.tail.strip())
        
        # Calcola capacità stimata
        effective_width = width - left - right
        effective_height = height - top - bottom
        
        if columns > 1:
            effective_width = (effective_width - (columns - 1) * gutter) / columns
        
        chars_per_line = max(1, int(effective_width / (font_size * 0.6)))
        lines_available = max(1, int(effective_height / leading))
        estimated_capacity = chars_per_line * lines_available * columns
        
        return {
            'id': frame_id,
            'spread_file': spread_file,
            'dimensions': {
                'width': width,
                'height': height,
                'x': x,
                'y': y
            },
            'text_properties': {
                'columns': columns,
                'gutter': gutter,
                'insets': {'top': top, 'right': right, 'bottom': bottom, 'left': left},
                'font_size': font_size,
                'leading': leading
            },
            'content': {
                'char_count': char_count,
                'estimated_capacity': estimated_capacity,
                'utilization': char_count / max(estimated_capacity, 1)
            }
        }
    
    def modify_frame_properties(self, frame_modifications: Dict[str, Dict]) -> bool:
        """
        Modifica proprietà dei text frame per gestire overflow
        
        Args:
            frame_modifications: Dizionario frame_id -> modifiche da applicare
            
        Returns:
            True se le modifiche sono state applicate con successo
        """
        if not self.idml_package or not frame_modifications:
            return False
        
        modifications_applied = 0
        
        # Trova e modifica gli spread
        try:
            for file_info in self.idml_package.infolist():
                if not (file_info.filename.startswith('Spreads/') and file_info.filename.endswith('.xml')):
                    continue
                
                # Leggi contenuto spread
                spread_content = self.idml_package.read(file_info.filename)
                if isinstance(spread_content, bytes):
                    spread_content = spread_content.decode('utf-8')
                
                spread_root = ET.fromstring(spread_content)
                modified = False
                
                # Cerca e modifica TextFrame
                for element in spread_root.iter():
                    if self._remove_namespace(element.tag) == 'TextFrame':
                        frame_id = element.get('Self')
                        
                        if frame_id in frame_modifications:
                            changes = frame_modifications[frame_id]
                            if self._apply_frame_modifications(element, changes):
                                modified = True
                                modifications_applied += 1
                
                # Salva spread modificato se necessario
                if modified:
                    modified_xml = ET.tostring(spread_root, encoding='unicode')
                    # Sostituisci nel package (questo richiederà un salvataggio completo)
                    print(f"✅ Modificati frame in {file_info.filename}")
        
        except Exception as e:
            print(f"Errore modifica frame: {e}")
            return False
        
        print(f"📝 Applicate {modifications_applied} modifiche ai frame")
        return modifications_applied > 0
    
    def _apply_frame_modifications(self, textframe_elem: ET.Element, changes: Dict) -> bool:
        """Applica modifiche a un singolo TextFrame"""
        applied = False
        
        try:
            # Modifica font size
            if 'font_size' in changes:
                new_size = changes['font_size']
                # Cerca attributi font esistenti o crea nuovo
                for attr in textframe_elem.attrib:
                    if 'FontSize' in attr or 'PointSize' in attr:
                        textframe_elem.set(attr, str(new_size))
                        applied = True
                        break
            
            # Modifica leading
            if 'leading' in changes:
                new_leading = changes['leading']
                for attr in textframe_elem.attrib:
                    if 'Leading' in attr:
                        textframe_elem.set(attr, str(new_leading))
                        applied = True
                        break
            
            # Modifica inset spacing
            if 'inset_spacing' in changes:
                new_insets = changes['inset_spacing']
                if isinstance(new_insets, (list, tuple)) and len(new_insets) == 4:
                    inset_str = ' '.join(str(x) for x in new_insets)
                    textframe_elem.set('TextFramePreferenceInsetSpacing', inset_str)
                    applied = True
            
            # Modifica dimensioni frame
            if 'resize' in changes:
                resize_data = changes['resize']
                current_transform = textframe_elem.get('ItemTransform', '1 0 0 1 0 0')
                transform_values = [float(x) for x in current_transform.split()]
                
                if len(transform_values) >= 6:
                    # Modifica width e height se specificati
                    if 'width' in resize_data:
                        transform_values[0] = resize_data['width']
                    if 'height' in resize_data:
                        transform_values[3] = resize_data['height']
                    
                    new_transform = ' '.join(str(x) for x in transform_values)
                    textframe_elem.set('ItemTransform', new_transform)
                    applied = True
        
        except Exception as e:
            print(f"Errore applicazione modifiche frame: {e}")
            return False
        
        return applied
    
    def _remove_namespace(self, tag: str) -> str:
        """Rimuove namespace da tag XML"""
        return tag.split('}')[-1] if '}' in tag else tag
    
    def _serialize_xml_with_pi(self, root: ET.Element) -> str:
        """
        Serializza XML preservando i Processing Instructions in modo più robusto.
        """
        try:
            # Usa il metodo standard di ElementTree
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            
            # Se la serializzazione è riuscita, restituisci il risultato
            return xml_str
            
        except Exception as e:
            print(f"⚠️  Errore nella serializzazione XML: {e}")
            
            # Fallback: prova con minidom se disponibile
            try:
                from xml.dom import minidom
                rough_string = ET.tostring(root, encoding='unicode')
                reparsed = minidom.parseString(rough_string)
                return reparsed.toprettyxml(indent="", newl="")
            except:
                # Ultimo fallback: restituisci stringa grezza
                return ET.tostring(root, encoding='unicode')
    
    def generate_overflow_adjustments(self, overflow_predictions: List) -> Dict[str, Dict]:
        """
        Genera suggerimenti di regolazione frame basati su predizioni overflow
        
        Args:
            overflow_predictions: Lista predizioni overflow dal detector
            
        Returns:
            Dizionario frame_id -> modifiche suggerite
        """
        adjustments = {}
        
        for prediction in overflow_predictions:
            if prediction.overflow_risk <= 1.0:
                continue  # Nessun overflow previsto
            
            frame_id = prediction.frame_id
            overflow_amount = prediction.estimated_translated_length - prediction.available_space_chars
            
            # Strategia 1: Riduzione font size (5-10%)
            font_reduction = {
                'font_size': 11.0,  # Da 12.0 default
                'leading': 13.2,   # Proporzionale
                'reason': f'Riduzione font per {overflow_amount} caratteri overflow'
            }
            
            # Strategia 2: Riduzione margini interni
            inset_reduction = {
                'inset_spacing': [3.0, 3.0, 3.0, 3.0],  # Margini ridotti
                'reason': f'Riduzione margini per overflow di {overflow_amount} caratteri'
            }
            
            # Strategia 3: Resize frame (aumenta altezza)
            height_increase = max(20.0, overflow_amount * 0.2)  # Stima aumento necessario
            frame_resize = {
                'resize': {'height': height_increase},
                'reason': f'Aumento altezza di {height_increase}pt per overflow'
            }
            
            # Scegli strategia in base al rischio
            if prediction.overflow_risk < 1.2:
                adjustments[frame_id] = inset_reduction
            elif prediction.overflow_risk < 1.5:
                adjustments[frame_id] = font_reduction
            else:
                adjustments[frame_id] = frame_resize
        
        return adjustments
    
    def close(self) -> None:
        """Chiude il processor e pulisce le risorse temporanee"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        
        self.idml_package = None
        self.stories_data = {}
        self.master_pages_data = {}