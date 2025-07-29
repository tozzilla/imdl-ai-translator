"""
Document Analyzer - Analizza documenti IDML prima della traduzione per migliorare il contesto
"""

import re
from typing import Dict, List, Tuple, Set, Optional
from collections import Counter, defaultdict
from xml.etree import ElementTree as ET
import logging

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """Analizza documenti IDML per estrarre contesto, terminologia e struttura"""
    
    def __init__(self):
        """Inizializza l'analizzatore"""
        self.document_info = {}
        self.terminology = {}
        self.structure = {}
        self.references = {}
        self.context_clues = []
        
    def analyze_document(self, stories_data: Dict, document_info: Dict) -> Dict:
        """
        Analizza completamente un documento IDML
        
        Args:
            stories_data: Dati delle stories dal IDMLProcessor
            document_info: Informazioni base del documento
            
        Returns:
            Dizionario con analisi completa del documento
        """
        logger.info("🔍 Avvio analisi completa documento...")
        
        # Estrai tutto il testo dal documento
        all_texts = self._extract_all_texts(stories_data)
        
        # Analisi componenti
        self.document_info = document_info
        self.terminology = self._extract_terminology(all_texts)
        self.structure = self._analyze_structure(stories_data, all_texts)
        self.references = self._extract_references(all_texts)
        self.context_clues = self._detect_context_clues(all_texts)
        
        # Costruisci analisi finale
        analysis = {
            'document_type': self._determine_document_type(),
            'domain': self._determine_domain(),
            'terminology': self.terminology,
            'structure': self.structure,
            'references': self.references,
            'context_clues': self.context_clues,
            'translation_context': self._build_translation_context(),
            'quality_indicators': self._assess_quality_indicators(all_texts)
        }
        
        logger.info(f"✅ Analisi completata - Tipo: {analysis['document_type']}, Dominio: {analysis['domain']}")
        return analysis
    
    def _extract_all_texts(self, stories_data: Dict) -> List[str]:
        """Estrae tutti i testi dal documento per l'analisi"""
        all_texts = []
        
        for story_name, story_data in stories_data.items():
            story_root = story_data['root']
            
            # Estrai tutto il testo, anche quello che normalmente non sarebbe tradotto
            for elem in story_root.iter():
                if elem.text and elem.text.strip():
                    all_texts.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    all_texts.append(elem.tail.strip())
        
        return all_texts
    
    def _extract_terminology(self, texts: List[str]) -> Dict:
        """Estrae terminologia tecnica e nomi prodotto dal documento"""
        terminology = {
            'product_names': set(),
            'technical_terms': set(),
            'measurements': set(),
            'materials': set(),
            'repeated_terms': {},
            'acronyms': set()
        }
        
        # Contatori per identificare termini ripetuti
        term_counter = Counter()
        
        for text in texts:
            words = text.split()
            
            # Cerca pattern specifici
            terminology['product_names'].update(self._find_product_names(text))
            terminology['technical_terms'].update(self._find_technical_terms(text))
            terminology['measurements'].update(self._find_measurements(text))
            terminology['materials'].update(self._find_materials(text))
            terminology['acronyms'].update(self._find_acronyms(text))
            
            # Conta termini per identificare quelli ricorrenti
            for word in words:
                if len(word) > 3:  # Solo parole significative
                    term_counter[word.lower()] += 1
        
        # Identifica termini ripetuti (potenzialmente importanti)
        terminology['repeated_terms'] = {
            term: count for term, count in term_counter.items() 
            if count >= 3 and len(term) > 4
        }
        
        return terminology
    
    def _find_product_names(self, text: str) -> Set[str]:
        """Identifica nomi di prodotti nel testo"""
        product_patterns = [
            r'\\b(Skyfix-[A-Z]\\d*)\\b',
            r'\\b(SafeGuard\\s+\\w+)\\b',
            r'\\b(Falz\\s*Single)\\b',
            r'\\b([A-Z][a-z]+[-\\s][A-Z]\\d*)\\b',  # Pattern generale prodotti
        ]
        
        products = set()
        for pattern in product_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            products.update(matches)
        
        return products
    
    def _find_technical_terms(self, text: str) -> Set[str]:
        """Identifica termini tecnici"""
        # Termini che indicano contenuto tecnico
        technical_indicators = [
            r'\\b\\d+\\s*kN\\b', r'\\b\\d+\\s*mm\\b', r'\\b\\d+\\s*cm\\b',
            r'\\bEN\\s*\\d+\\b', r'\\bDIN\\s*\\d+\\b', r'\\bISO\\s*\\d+\\b',
            r'\\b[A-Z]{2,4}\\d+\\b',  # Codici standard
        ]
        
        terms = set()
        for pattern in technical_indicators:
            matches = re.findall(pattern, text)
            terms.update(matches)
        
        return terms
    
    def _find_measurements(self, text: str) -> Set[str]:
        """Identifica misure e unità"""
        measurement_pattern = r'\\b\\d+(?:[.,]\\d+)?\\s*(?:mm|cm|m|kg|kN|daN|Pa|MPa|°C)\\b'
        return set(re.findall(measurement_pattern, text))
    
    def _find_materials(self, text: str) -> Set[str]:
        """Identifica materiali tecnici"""
        material_keywords = [
            'acciaio', 'legno', 'calcestruzzo', 'metallo', 'plastica',
            'EPDM', 'TPO', 'PVC', 'alluminio', 'zinco'
        ]
        
        materials = set()
        for keyword in material_keywords:
            if keyword.lower() in text.lower():
                materials.add(keyword)
        
        return materials
    
    def _find_acronyms(self, text: str) -> Set[str]:
        """Identifica acronimi (es. CE, EN, DIN)"""
        acronym_pattern = r'\\b[A-Z]{2,5}\\b'
        acronyms = set(re.findall(acronym_pattern, text))
        
        # Filtra acronimi comuni che non sono tecnici
        common_words = {'THE', 'AND', 'FOR', 'YOU', 'ARE', 'NOT', 'ALL'}
        return acronyms - common_words
    
    def _analyze_structure(self, stories_data: Dict, texts: List[str]) -> Dict:
        """Analizza la struttura del documento"""
        structure = {
            'sections': [],
            'page_references': [],
            'navigation_elements': [],
            'warnings_safety': [],
            'instruction_sequences': []
        }
        
        # Identifica sezioni basate su pattern testuali
        section_indicators = [
            'installazione', 'montaggio', 'sicurezza', 'avvertenze',
            'attenzione', 'pericolo', 'istruzioni', 'materiali'
        ]
        
        for text in texts:
            text_lower = text.lower()
            
            # Identifica sezioni
            for indicator in section_indicators:
                if indicator in text_lower:
                    structure['sections'].append({
                        'type': indicator,
                        'text': text[:100]  # Prime 100 caratteri
                    })
            
            # Identifica riferimenti pagina
            page_refs = re.findall(r'pag\\.\\s*\\d+|p\\.\\s*\\d+|>>.*pag', text.lower())
            structure['page_references'].extend(page_refs)
            
            # Identifica elementi di navigazione
            if '>>' in text or 'vedi' in text_lower or 'consultare' in text_lower:
                structure['navigation_elements'].append(text)
            
            # Identifica avvertenze di sicurezza
            safety_words = ['pericolo', 'attenzione', 'avvertenza', 'evitare']
            if any(word in text_lower for word in safety_words):
                structure['warnings_safety'].append(text)
        
        return structure
    
    def _extract_references(self, texts: List[str]) -> Dict:
        """Estrae tutti i riferimenti interni del documento"""
        references = {
            'page_numbers': set(),
            'page_ranges': [],
            'section_refs': [],
            'figure_refs': [],
            'cross_references': []
        }
        
        for text in texts:
            # Numeri di pagina standalone
            page_nums = re.findall(r'\\b(\\d{1,2})\\b', text)
            references['page_numbers'].update(page_nums)
            
            # Range di pagine
            page_ranges = re.findall(r'(\\d+)\\s*-\\s*(\\d+)', text)
            references['page_ranges'].extend(page_ranges)
            
            # Riferimenti a figure
            fig_refs = re.findall(r'figura\\s*(\\d+)', text.lower())
            references['figure_refs'].extend(fig_refs)
            
            # Altri riferimenti incrociati
            if 'vedi' in text.lower() or 'consultare' in text.lower():
                references['cross_references'].append(text)
        
        return references
    
    def _detect_context_clues(self, texts: List[str]) -> List[str]:
        """Rileva indizi di contesto per migliorare la traduzione"""
        context_clues = []
        
        # Indizi per tipo di documento
        if any('sicurezza' in text.lower() for text in texts):
            context_clues.append('safety_manual')
        
        if any('installazione' in text.lower() or 'montaggio' in text.lower() for text in texts):
            context_clues.append('installation_guide')
        
        if any('specifiche' in text.lower() or 'caratteristiche' in text.lower() for text in texts):
            context_clues.append('technical_specification')
        
        # Indizi per settore
        construction_terms = ['tetto', 'copertura', 'edificio', 'costruzione']
        if any(term in ' '.join(texts).lower() for term in construction_terms):
            context_clues.append('construction_industry')
        
        safety_terms = ['anticaduta', 'protezione', 'imbracatura', 'ancoraggio']
        if any(term in ' '.join(texts).lower() for term in safety_terms):
            context_clues.append('fall_protection')
        
        return list(set(context_clues))  # Rimuovi duplicati
    
    def _determine_document_type(self) -> str:
        """Determina il tipo di documento basato sull'analisi"""
        if 'safety_manual' in self.context_clues:
            return 'safety_manual'
        elif 'installation_guide' in self.context_clues:
            return 'installation_manual'
        elif 'technical_specification' in self.context_clues:
            return 'technical_specification'
        else:
            return 'technical_document'
    
    def _determine_domain(self) -> str:
        """Determina il dominio tecnico"""
        if 'fall_protection' in self.context_clues:
            return 'safety'
        elif 'construction_industry' in self.context_clues:
            return 'construction'
        else:
            return 'technical'
    
    def _build_translation_context(self) -> str:
        """Costruisce contesto dettagliato per la traduzione"""
        doc_type = self._determine_document_type()
        domain = self._determine_domain()
        
        context_parts = []
        
        # Tipo documento
        if doc_type == 'safety_manual':
            context_parts.append("This is a SAFETY MANUAL for fall protection systems")
        elif doc_type == 'installation_manual':
            context_parts.append("This is an INSTALLATION MANUAL for construction equipment")
        elif doc_type == 'technical_specification':
            context_parts.append("This is a TECHNICAL SPECIFICATION document")
        
        # Dominio
        if domain == 'safety':
            context_parts.append("Focus on safety terminology and formal language")
        elif domain == 'construction':
            context_parts.append("Focus on construction and building terminology")
        
        # Prodotti identificati
        if self.terminology['product_names']:
            products = list(self.terminology['product_names'])[:3]  # Primi 3
            context_parts.append(f"Key products mentioned: {', '.join(products)}")
        
        # Termini tecnici
        if self.terminology['technical_terms']:
            context_parts.append("Contains technical specifications and measurements")
        
        return ". ".join(context_parts) + "."
    
    def _assess_quality_indicators(self, texts: List[str]) -> Dict:
        """Valuta indicatori di qualità per guidare la traduzione"""
        total_text = ' '.join(texts)
        
        return {
            'complexity_score': self._calculate_complexity(texts),
            'technical_density': len(self.terminology['technical_terms']) / len(texts) if texts else 0,
            'repetition_factor': len(self.terminology['repeated_terms']),
            'reference_count': len(self.references.get('page_references', [])),
            'has_safety_content': any('sicurezza' in text.lower() for text in texts),
            'estimated_translation_time': len(total_text) / 1000  # Rough estimate
        }
    
    def _calculate_complexity(self, texts: List[str]) -> float:
        """Calcola un punteggio di complessità del documento"""
        if not texts:
            return 0.0
        
        # Fattori di complessità
        avg_word_length = sum(len(word) for text in texts for word in text.split()) / sum(len(text.split()) for text in texts) if texts else 0
        technical_terms_ratio = len(self.terminology['technical_terms']) / len(texts)
        acronym_density = len(self.terminology['acronyms']) / len(texts)
        
        # Punteggio combinato (0-1)
        complexity = min(1.0, (avg_word_length / 10) + technical_terms_ratio + acronym_density)
        
        return round(complexity, 2)
    
    def get_analysis_summary(self) -> str:
        """Restituisce un riassunto dell'analisi per il logging"""
        if not hasattr(self, 'terminology'):
            return "Analisi non ancora eseguita"
        
        return f"""
📋 ANALISI DOCUMENTO:
• Tipo: {self._determine_document_type()}
• Dominio: {self._determine_domain()}  
• Prodotti trovati: {len(self.terminology['product_names'])}
• Termini tecnici: {len(self.terminology['technical_terms'])}
• Riferimenti pagina: {len(self.references.get('page_references', []))}
• Contesto: {', '.join(self.context_clues)}
        """.strip()