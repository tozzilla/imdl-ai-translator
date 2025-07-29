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
        self.temp_dir = None
        
        if not self.idml_path.exists():
            raise FileNotFoundError(f"File IDML non trovato: {idml_path}")
            
    def load_idml(self) -> None:
        """Carica il file IDML in memoria"""
        try:
            self.idml_package = idml.IDMLPackage(str(self.idml_path))
            self._extract_stories()
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
            # Prima salva tutti i processing instructions
            processing_instructions = []
            for child in list(story_root):
                if child.tag.startswith('<?') or hasattr(child, 'tag') and child.tag == ET.PI:
                    processing_instructions.append(child)
            
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
            for pi in processing_instructions:
                if pi.getparent() is None:  # Se è stato scollegato
                    story_root.insert(0, pi)  # Reinserisci all'inizio
    
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
                        updated_xml = ET.tostring(self.stories_data[file_path]['root'], encoding='unicode')
                        new_zip.writestr(file_info, updated_xml)
                    # Se è una master page che abbiamo modificato, usa il contenuto tradotto
                    elif file_path in self.master_pages_data:
                        updated_xml = ET.tostring(self.master_pages_data[file_path]['root'], encoding='unicode')
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
            
        return {
            'filename': self.idml_path.name,
            'stories_count': len(self.stories_data),
            'stories_names': list(self.stories_data.keys())
        }
    
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