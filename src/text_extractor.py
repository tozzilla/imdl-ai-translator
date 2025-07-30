"""
Text Extractor - Estrae e organizza il testo dai file IDML per la traduzione
"""

import re
from typing import Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET

# Import del glossario
try:
    from config.glossary import TranslationGlossary, load_project_glossary
except ImportError:
    # Fallback se il glossario non è disponibile
    class TranslationGlossary:
        def is_protected_term(self, text): return False
        def create_protected_translation_note(self, text): return ""
    def load_project_glossary(path): return TranslationGlossary()


class TextExtractor:
    """Classe per estrarre e processare testo da contenuti IDML"""
    
    def __init__(self, project_path: Optional[str] = None):
        """
        Inizializza l'estrattore di testo
        
        Args:
            project_path: Path del progetto per caricare glossario personalizzato
        """
        self.text_segments = []
        self.text_mapping = {}
        
        # Carica glossario
        if project_path:
            self.glossary = load_project_glossary(project_path)
        else:
            self.glossary = TranslationGlossary()
        
    def extract_translatable_text(self, stories_data: Dict) -> List[Dict]:
        """
        Estrae tutto il testo traducibile dalle stories IDML
        
        Args:
            stories_data: Dizionario con i dati delle stories dal IDMLProcessor
            
        Returns:
            Lista di dizionari con testo e metadati per la traduzione
        """
        translatable_segments = []
        segment_id = 0
        
        for story_name, story_data in stories_data.items():
            story_root = story_data['root']
            
            # Estrae i segmenti di testo dalla story
            segments = self._extract_text_segments_from_story(story_root, story_name)
            
            for segment in segments:
                segment['id'] = segment_id
                segment['story_name'] = story_name
                translatable_segments.append(segment)
                segment_id += 1
                
        self.text_segments = translatable_segments
        return translatable_segments
    
    def _extract_text_segments_from_story(self, story_root: ET.Element, story_name: str) -> List[Dict]:
        """
        Estrae segmenti di testo da una singola story
        
        Args:
            story_root: Root element XML della story
            story_name: Nome della story
            
        Returns:
            Lista di segmenti di testo con metadati
        """
        segments = []
        
        # Cerca elementi di testo specifici di IDML
        text_elements = self._find_text_elements(story_root)
        
        # Applica il merging dei line break forzati
        text_elements = self._merge_forced_line_breaks(text_elements, story_root)
        
        for elem_info in text_elements:
            element = elem_info['element']
            text_content = elem_info['text']
            
            if self._is_translatable_text(text_content):
                segment = {
                    'original_text': text_content,
                    'element_tag': element.tag,
                    'element_path': self._get_element_path(element),
                    'attributes': dict(element.attrib),
                    'text_type': elem_info['text_type'],  # 'text' o 'tail'
                    'character_count': len(text_content),
                    'word_count': len(text_content.split()),
                    'merged_from_breaks': elem_info.get('merged_from_breaks', False)
                }
                segments.append(segment)
                
        return segments
    
    def _find_text_elements(self, root: ET.Element) -> List[Dict]:
        """
        Trova SOLO gli elementi Content che contengono testo traducibile nell'XML IDML
        
        Args:
            root: Root element da cui cercare
            
        Returns:
            Lista di dizionari con elementi e informazioni sul testo
        """
        text_elements = []
        
        # NUOVO APPROCCIO: cerca specificamente elementi Content dentro CharacterStyleRange
        # Struttura IDML: Story > ParagraphStyleRange > CharacterStyleRange > Content
        
        # Rimuovi namespace per semplificare la ricerca
        def remove_namespace(tag):
            return tag.split('}')[-1] if '}' in tag else tag
        
        # Cerca tutti i CharacterStyleRange
        for element in root.iter():
            element_tag = remove_namespace(element.tag)
            
            if element_tag == 'CharacterStyleRange':
                # Cerca elementi Content dentro questo CharacterStyleRange
                for content_elem in element:
                    content_tag = remove_namespace(content_elem.tag)
                    
                    if content_tag == 'Content':
                        # Estrai il testo solo dai Content elements
                        if content_elem.text and content_elem.text.strip():
                            text_elements.append({
                                'element': content_elem,
                                'text': content_elem.text.strip(),
                                'text_type': 'text',
                                'parent_style': element.get('AppliedCharacterStyle', 'default')
                            })
                        
                        # Content elements non dovrebbero avere tail text, ma controlliamo comunque
                        if content_elem.tail and content_elem.tail.strip():
                            text_elements.append({
                                'element': content_elem,
                                'text': content_elem.tail.strip(),
                                'text_type': 'tail',
                                'parent_style': element.get('AppliedCharacterStyle', 'default')
                            })
        
        return text_elements
    
    def _is_translatable_text(self, text: str) -> bool:
        """
        Determina se un testo è traducibile (esclude codici, numeri puri, etc.)
        
        Args:
            text: Testo da valutare
            
        Returns:
            True se il testo è traducibile
        """
        if not text or len(text.strip()) < 2:
            return False
        
        text_clean = text.strip()
            
        # NON escludere più numeri semplici!
        # I numeri di pagina nel documento (es. "16", "17") sono contenuto valido
        # che deve essere preservato nella traduzione
        # if text_clean.isdigit():
        #     return False
            
        # Esclude testi che sono solo punteggiatura
        if re.match(r'^[^\w\s]+$', text_clean):
            return False
            
        # Esclude codici e identificatori (es. "ID123", "CODE_ABC")
        # MA NON parole italiane comuni che potrebbero essere in maiuscolo
        # E NON esclude numeri puri (che devono essere preservati)
        if re.match(r'^[A-Z0-9_]+$', text_clean) and not text_clean.isdigit():
            # Lista di parole italiane comuni che devono essere tradotte anche se in maiuscolo
            italian_words_to_translate = {
                'EVITARE', 'LEGNO', 'CALCESTRUZZO', 'ACCIAIO', 'METALLO', 'PLASTICA', 'VETRO',
                'INSTALLAZIONE', 'MONTAGGIO', 'FISSAGGIO', 'SICUREZZA', 'PROTEZIONE', 
                'ATTENZIONE', 'PERICOLO', 'AVVERTENZA', 'MANUALE', 'ISTRUZIONI',
                'SISTEMA', 'ELEMENTO', 'COMPONENTE', 'DISPOSITIVO', 'STRUTTURA',
                'SUPERFICIE', 'MATERIALE', 'PRODOTTO', 'UTILIZZARE', 'VERIFICARE',
                'CONTROLLARE', 'ASSICURARE', 'SEGUIRE', 'RISPETTARE',
                # Aggiunte nuove parole non tradotte
                'INDICE', 'INTRODUZIONE', 'AVVERTENZE', 'MARCATURA', 'ASSISTENZA',
                'CAPITOLO', 'SEZIONE', 'PARAGRAFO', 'PAGINA', 'FIGURA', 'TABELLA',
                'ESEMPIO', 'NOTA', 'IMPORTANTE', 'AVVISO', 'INFORMAZIONE',
                'CONTENUTO', 'SOMMARIO', 'APPENDICE', 'ALLEGATO', 'RIFERIMENTO',
                'DESCRIZIONE', 'SPECIFICA', 'REQUISITO', 'PROCEDURA', 'OPERAZIONE',
                # Nuove aggiunte richieste
                'FISSAGGI', 'CODICE', 'PARTE', 'POSIZIONE', 'FINITURA', 'LINEA',
                # Parole dal manuale SafeGuard
                'GUIDA', 'MESSA', 'OPERA', 'TARGHETTE', 'ACCESSO', 'USO',
                'CERTIFICATI', 'DISPOSITIVI', 'ISPEZIONE', 'CONDIZIONI', 'GARANZIA',
                'INDICAZIONI', 'MANUTENZIONE'
            }
            
            # Se è una parola italiana comune, deve essere tradotta
            if text_clean in italian_words_to_translate:
                return True
            
            # Altrimenti escludi come codice/identificatore
            return False
            
        # Esclude URL e email
        if re.match(r'https?://|www\.|@.*\.|.*@.*', text_clean):
            return False
        
        # ===== NUOVI FILTRI SPECIFICI IDML =====
        
        # Esclude nomi di font comuni
        if self._is_font_name(text_clean):
            return False
            
        # Esclude pattern IDML tecnici
        if self._is_idml_technical_pattern(text_clean):
            return False
            
        # Esclude pattern numerazione pagine
        if self._is_page_number_pattern(text_clean):
            return False
            
        # Esclude colori e swatch IDML
        if self._is_color_swatch_pattern(text_clean):
            return False
        
        # Controlla glossario termini protetti
        if self.glossary.is_protected_term(text_clean):
            return False
            
        return True
    
    def _is_font_name(self, text: str) -> bool:
        """Identifica nomi di font"""
        common_fonts = [
            'arial', 'helvetica', 'times', 'calibri', 'georgia', 'verdana',
            'tahoma', 'trebuchet', 'comic sans', 'impact', 'lucida',
            'courier', 'palatino', 'garamond', 'futura', 'avenir',
            'source sans', 'source serif', 'open sans', 'roboto',
            'lato', 'montserrat', 'ubuntu', 'nunito', 'raleway',
            'metropolis', 'myriad', 'minion', 'proxima', 'gotham'
        ]
        
        # Parole che NON sono mai font anche se seguite da weight
        non_font_words = [
            # Strumenti e attrezzi
            'dachziegel', 'silikonpistole', 'drehmomentschlüssel', 'hammer', 'screwdriver',
            'drill', 'saw', 'chisel', 'wrench', 'pliers', 'level', 'measure',
            'schraubendreher', 'bohrer', 'säge', 'meißel', 'wasserwaage',
            
            # Materiali
            'concrete', 'steel', 'wood', 'plastic', 'metal', 'glass',
            'beton', 'stahl', 'holz', 'plastik', 'metall', 'glas',
            
            # Colori 
            'red', 'blue', 'green', 'yellow', 'black', 'white',
            'rot', 'blau', 'grün', 'gelb', 'schwarz', 'weiß',
            
            # Altri oggetti comuni
            'window', 'door', 'roof', 'wall', 'floor', 'ceiling',
            'fenster', 'tür', 'dach', 'wand', 'boden', 'decke'
        ]
        
        text_lower = text.lower()
        
        # Controllo se inizia con parola che non è mai un font
        for non_font in non_font_words:
            if text_lower.startswith(non_font + ' ') or text_lower.startswith(non_font + '-'):
                return False
        
        # Controllo esatto
        if text_lower in common_fonts:
            return True
            
        # Controllo se inizia con nome font + variante
        for font in common_fonts:
            if text_lower.startswith(font + ' ') or text_lower.startswith(font + '-'):
                return True
                
        # Pattern font con peso/stile - ma solo per parole che sembrano realmente font
        # Evitiamo parole tedesche lunghe o composte
        if len(text.split()) == 2:  # Solo due parole
            base_word = text.split()[0].lower()
            weight = text.split()[1].lower()
            
            if (weight in ['regular', 'bold', 'light', 'medium', 'thin', 'black', 'italic', 'oblique'] and
                base_word not in non_font_words and 
                len(base_word) <= 12 and  # Font names are usually short
                not any(char in base_word for char in 'äöüß')):  # Avoid German compound words
                return True
            
        return False
    
    def _is_idml_technical_pattern(self, text: str) -> bool:
        """Identifica pattern tecnici IDML"""
        
        # Swatch patterns
        if text.startswith('Swatch/') or text.startswith('Color/'):
            return True
            
        # CMYK/RGB color values
        if re.match(r'^(C|M|Y|K|R|G|B)=\d+', text):
            return True
            
        # Pattern color con valori (es. "C=0 M=0 Y=0 K=9")
        if re.match(r'^(Color/)?[CMYKRGB]=[0-9\s=CMYKRGB]+$', text):
            return True
            
        # Style references
        if re.match(r'^(Character|Paragraph)Style/', text):
            return True
            
        # IDML IDs e self references
        if re.match(r'^[a-z]+[0-9a-f]{4,}$', text.lower()):
            return True
            
        return False
    
    def _is_page_number_pattern(self, text: str) -> bool:
        """Identifica pattern di numerazione pagine che NON devono essere tradotti"""
        
        # CRITICO: Dobbiamo distinguere tra:
        # 1. Numeri di pagina che sono CONTENUTO (da preservare): "16", "17" nel testo
        # 2. Riferimenti che devono essere tradotti: "pag. 16", ">> pag. 16 - pag. 19" 
        # 3. Numerazione automatica da escludere: numeri isolati senza contesto
        
        text_clean = text.strip()
        
        # NON escludere più i numeri standalone!
        # I numeri di pagina nel documento sono contenuto valido che deve rimanere
        
        # Esclude SOLO pattern molto specifici che sono chiaramente tecnici:
        # - Numeri molto lunghi (probabilmente ID)
        if re.match(r'^\d{4,}$', text_clean):
            return True
            
        # - Numeri con pattern ID (es. "00123", "0001")
        if re.match(r'^0+\d+$', text_clean) and len(text_clean) > 2:
            return True
            
        return False
    
    def _is_color_swatch_pattern(self, text: str) -> bool:
        """Identifica pattern colori e swatch"""
        
        # None swatch
        if text.lower() in ['none', 'swatch/none']:
            return True
            
        # Hex colors
        if re.match(r'^#[0-9a-f]{3,8}$', text.lower()):
            return True
            
        # Pantone colors
        if re.match(r'^pantone\s+\d+', text.lower()):
            return True
            
        return False
    
    def _get_element_path(self, element: ET.Element) -> str:
        """
        Ottiene il path XPath dell'elemento nell'albero XML
        
        Args:
            element: Elemento di cui ottenere il path
            
        Returns:
            Stringa rappresentante il path dell'elemento
        """
        path_parts = []
        current = element
        
        # Risale l'albero per costruire il path
        while current is not None:
            tag = current.tag
            # Aggiungi attributi identificativi se presenti
            if 'Self' in current.attrib:
                tag += f"[@Self='{current.attrib['Self']}']"
            elif 'id' in current.attrib:
                tag += f"[@id='{current.attrib['id']}']"
                
            path_parts.insert(0, tag)
            current = current.getparent() if hasattr(current, 'getparent') else None
            
        return '/' + '/'.join(path_parts)
    
    def prepare_for_translation(self, segments: List[Dict]) -> List[str]:
        """
        Prepara i segmenti di testo per l'invio al servizio di traduzione
        
        Args:
            segments: Lista di segmenti estratti
            
        Returns:
            Lista di stringhe pronte per la traduzione
        """
        texts_to_translate = []
        
        for segment in segments:
            # Pulisce e prepara il testo per la traduzione
            cleaned_text = self._clean_text_for_translation(segment['original_text'])
            
            # Aggiunge note sui termini protetti se presenti
            protected_note = self.glossary.create_protected_translation_note(cleaned_text)
            if protected_note:
                # Prepende la nota al testo
                cleaned_text = f"[{protected_note}] {cleaned_text}"
            
            texts_to_translate.append(cleaned_text)
            
        return texts_to_translate
    
    def _clean_text_for_translation(self, text: str) -> str:
        """
        Pulisce il testo rimuovendo caratteri speciali che potrebbero interferire
        
        Args:
            text: Testo da pulire
            
        Returns:
            Testo pulito per la traduzione
        """
        # Rimuove caratteri di controllo invisibili
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        
        # Normalizza spazi multipli
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Rimuove spazi iniziali/finali
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _merge_forced_line_breaks(self, text_elements: List[Dict], story_root: ET.Element) -> List[Dict]:
        """
        Rileva e unisce testi separati da line break forzati nel mezzo di frasi.
        
        IDML può contenere:
        - <Br/> tags per forced line breaks
        - Tabs e spazi usati per allineamento che spezzano frasi
        - Soft returns che dividono il testo in elementi separati
        
        Args:
            text_elements: Lista elementi testo trovati
            story_root: Root della story per analisi contestuale
            
        Returns:
            Lista elementi con testi uniti dove appropriato
        """
        if not text_elements:
            return text_elements
        
        merged_elements = []
        i = 0
        
        while i < len(text_elements):
            current = text_elements[i]
            text = current['text']
            
            # Criteri per identificare testo che potrebbe continuare
            # 1. Termina senza punteggiatura finale
            # 2. Non è un titolo (tutto maiuscolo)
            # 3. Ha lunghezza ragionevole per essere parte di frase
            needs_merge = (
                not re.search(r'[.!?:]\s*$', text) and  # No punteggiatura finale
                not text.isupper() and  # Non è un titolo
                len(text) > 5 and  # Non troppo corto
                i + 1 < len(text_elements)  # C'è un elemento successivo
            )
            
            if needs_merge:
                # Guarda gli elementi successivi per potenziale continuazione
                merged_text = text
                merged_count = 0
                j = i + 1
                
                while j < len(text_elements) and merged_count < 3:  # Max 3 merge per sicurezza
                    next_elem = text_elements[j]
                    next_text = next_elem['text']
                    
                    # Controlla se il prossimo elemento sembra una continuazione
                    if self._is_continuation(text, next_text):
                        # Verifica che siano nello stesso contesto (stesso ParagraphStyleRange)
                        if self._same_paragraph_context(current, next_elem):
                            # Unisci con spazio appropriato
                            separator = ' '
                            
                            # Se il testo corrente termina con trattino, potrebbe essere sillabazione
                            if text.endswith('-'):
                                # Rimuovi trattino e unisci direttamente
                                merged_text = merged_text[:-1] + next_text
                            else:
                                merged_text = merged_text + separator + next_text
                            
                            merged_count += 1
                            j += 1
                            
                            # Se troviamo punteggiatura finale, ferma il merge
                            if re.search(r'[.!?]\s*$', next_text):
                                break
                        else:
                            break
                    else:
                        break
                
                # Se abbiamo fatto dei merge, crea elemento unito
                if merged_count > 0:
                    merged_elem = current.copy()
                    merged_elem['text'] = merged_text
                    merged_elem['merged_from_breaks'] = True
                    merged_elem['merge_count'] = merged_count
                    merged_elements.append(merged_elem)
                    
                    # Salta gli elementi che sono stati uniti
                    i = j
                    continue
            
            # Aggiungi elemento non modificato
            merged_elements.append(current)
            i += 1
        
        # Log merge effettuati
        merge_count = sum(1 for e in merged_elements if e.get('merged_from_breaks', False))
        if merge_count > 0:
            print(f"   📝 Unite {merge_count} frasi spezzate da line break forzati")
        
        return merged_elements
    
    def _is_continuation(self, prev_text: str, next_text: str) -> bool:
        """
        Determina se next_text è probabilmente una continuazione di prev_text.
        """
        # Il testo successivo inizia con minuscola (forte indicatore di continuazione)
        if next_text and next_text[0].islower():
            return True
        
        # Il testo precedente termina con virgola o punto e virgola
        if re.search(r'[,;]\s*$', prev_text):
            return True
        
        # Il testo precedente termina con congiunzione o preposizione
        conjunctions = ['e', 'ed', 'o', 'od', 'ma', 'però', 'quindi', 'perché', 
                       'and', 'or', 'but', 'however', 'therefore', 'because',
                       'und', 'oder', 'aber', 'jedoch', 'daher', 'weil']
        
        words = prev_text.split()
        if words and words[-1].lower() in conjunctions:
            return True
        
        # Il testo precedente termina con articolo o preposizione
        articles_preps = ['il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
                         'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
                         'the', 'a', 'an', 'of', 'to', 'from', 'in', 'with', 'on',
                         'der', 'die', 'das', 'ein', 'eine', 'von', 'zu', 'mit']
        
        if words and words[-1].lower() in articles_preps:
            return True
        
        return False
    
    def _same_paragraph_context(self, elem1: Dict, elem2: Dict) -> bool:
        """
        Verifica se due elementi appartengono allo stesso contesto di paragrafo.
        """
        # Per ora assumiamo che elementi consecutivi siano nello stesso contesto
        # In futuro potremmo verificare il parent ParagraphStyleRange
        return True
    
    def map_translations_to_segments(self, segments: List[Dict], translations: List[str]) -> Dict[str, List[str]]:
        """
        Mappa le traduzioni ricevute ai segmenti originali organizzati per story
        
        Args:
            segments: Segmenti originali estratti
            translations: Lista delle traduzioni ricevute
            
        Returns:
            Dizionario story_name -> lista traduzioni per quella story
        """
        if len(segments) != len(translations):
            raise ValueError(f"Numero di segmenti ({len(segments)}) != numero traduzioni ({len(translations)})")
        
        story_translations = {}
        
        for i, segment in enumerate(segments):
            story_name = segment['story_name']
            translation = translations[i]
            
            if story_name not in story_translations:
                story_translations[story_name] = []
                
            story_translations[story_name].append(translation)
            
        return story_translations
    
    def get_translation_stats(self, segments: List[Dict]) -> Dict[str, int]:
        """
        Calcola statistiche sui testi da tradurre
        
        Args:
            segments: Lista di segmenti estratti
            
        Returns:
            Dizionario con statistiche
        """
        total_chars = sum(segment['character_count'] for segment in segments)
        total_words = sum(segment['word_count'] for segment in segments)
        stories_count = len(set(segment['story_name'] for segment in segments))
        
        return {
            'total_segments': len(segments),
            'total_characters': total_chars,
            'total_words': total_words,
            'stories_count': stories_count,
            'avg_chars_per_segment': total_chars // len(segments) if segments else 0
        }