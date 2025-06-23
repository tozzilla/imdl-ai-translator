"""
Glossario di termini e nomi prodotti che non devono essere tradotti
"""

from typing import Dict, List, Set
import re


class TranslationGlossary:
    """Gestisce glossario di termini che non devono essere tradotti"""
    
    def __init__(self):
        """Inizializza il glossario con termini predefiniti"""
        
        # Nomi di prodotti (case-insensitive)
        self.product_names = {
            # Passerelle e strutture
            'myriad', 'infinity', 'falz', 'falz single',
            
            # Marchi e aziende (comuni in documentazione tecnica)
            'würth', 'hilti', 'simpson', 'fischer',
            'sika', 'mapei', 'weber', 'knauf',
            
            # Prodotti specifici
            'eurocod', 'eurocode', 'din', 'en', 'iso',
            'ce', 'eot', 'eta', 'dop',
        }
        
        # Termini tecnici specifici (case-sensitive per precisione)
        self.technical_terms = {
            'EPDM', 'TPO', 'PVC', 'PE', 'PP', 'PU',
            'XLPE', 'NBR', 'SBR', 'PTFE',
            'CE', 'EN', 'DIN', 'ISO', 'UNI',
            'kN', 'kN/m', 'kg/m²', 'mm', 'cm', 'm',
            'N/mm²', 'MPa', 'GPa', 'Hz',
        }
        
        # Codici e riferimenti
        self.reference_patterns = [
            r'^[A-Z]{2,5}-\d+',  # Es: DIN-1234, EN-5678
            r'^\d{4}-\d{1,2}',   # Es: 2024-1, 1995-3
            r'^[A-Z]\d+[A-Z]?$', # Es: M8, S355, C25/30
            r'^[A-Z]{1,3}\d{2,4}$', # Es: S355, C25
        ]
    
    def is_protected_term(self, text: str) -> bool:
        """
        Verifica se un termine è protetto (non deve essere tradotto)
        
        Args:
            text: Testo da verificare
            
        Returns:
            True se il termine è protetto
        """
        text_clean = text.strip()
        
        # Controllo nomi prodotti (case-insensitive)
        if text_clean.lower() in self.product_names:
            return True
            
        # Controllo termini tecnici (case-sensitive)
        if text_clean in self.technical_terms:
            return True
            
        # Controllo pattern di riferimenti
        for pattern in self.reference_patterns:
            if re.match(pattern, text_clean):
                return True
                
        return False
    
    def add_product_name(self, name: str) -> None:
        """Aggiunge un nome prodotto al glossario"""
        self.product_names.add(name.lower())
    
    def add_technical_term(self, term: str) -> None:
        """Aggiunge un termine tecnico al glossario"""
        self.technical_terms.add(term)
    
    def load_custom_glossary(self, file_path: str) -> None:
        """
        Carica un glossario personalizzato da file
        
        Args:
            file_path: Path al file glossario
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Formato: tipo:termine
                        if ':' in line:
                            term_type, term = line.split(':', 1)
                            if term_type.lower() == 'product':
                                self.add_product_name(term)
                            elif term_type.lower() == 'technical':
                                self.add_technical_term(term)
                        else:
                            # Default: prodotto
                            self.add_product_name(line)
        except FileNotFoundError:
            pass  # Glossario opzionale
    
    def get_protected_terms_in_text(self, text: str) -> List[str]:
        """
        Trova tutti i termini protetti in un testo
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Lista di termini protetti trovati
        """
        protected = []
        
        # Dividi in parole mantenendo punteggiatura
        words = re.findall(r'\b\w+(?:[.-]\w+)*\b', text)
        
        for word in words:
            if self.is_protected_term(word):
                protected.append(word)
                
        return protected
    
    def create_protected_translation_note(self, text: str) -> str:
        """
        Crea una nota per il traduttore sui termini protetti
        
        Args:
            text: Testo da tradurre
            
        Returns:
            Nota sui termini da non tradurre
        """
        protected_terms = self.get_protected_terms_in_text(text)
        
        if protected_terms:
            unique_terms = list(set(protected_terms))
            return f"IMPORTANT: Keep these terms unchanged: {', '.join(unique_terms)}"
        
        return ""


# Istanza globale del glossario
default_glossary = TranslationGlossary()


def is_protected_term(text: str) -> bool:
    """Funzione di convenienza per verificare termini protetti"""
    return default_glossary.is_protected_term(text)


def load_project_glossary(project_path: str) -> TranslationGlossary:
    """
    Carica glossario specifico per progetto
    
    Args:
        project_path: Path alla directory del progetto
        
    Returns:
        Istanza glossario configurata
    """
    import os
    
    glossary = TranslationGlossary()
    
    # Cerca file glossario nella directory del progetto
    glossary_files = [
        os.path.join(project_path, 'glossary.txt'),
        os.path.join(project_path, 'config', 'glossary.txt'),
        os.path.join(project_path, '.glossary'),
    ]
    
    for file_path in glossary_files:
        if os.path.exists(file_path):
            glossary.load_custom_glossary(file_path)
            break
    
    return glossary


if __name__ == '__main__':
    # Test del glossario
    glossary = TranslationGlossary()
    
    test_terms = [
        'Myriad',
        'falz single', 
        'CE',
        'DIN-1234',
        'normale testo',
        'kN/m',
        'M8',
        'questo è testo normale'
    ]
    
    print("🔍 Test Glossario:")
    for term in test_terms:
        is_protected = glossary.is_protected_term(term)
        status = "🔒 PROTETTO" if is_protected else "✅ Traducibile"
        print(f"  '{term}' -> {status}")
    
    print("\n📝 Test nota traduzione:")
    test_text = "Installare Falz Single con viti M8 secondo norma DIN-1234"
    note = glossary.create_protected_translation_note(test_text)
    print(f"Testo: {test_text}")
    print(f"Nota: {note}")