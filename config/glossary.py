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
            # Aggiunte per strumenti e avvertenze
            'EVITARE', 'AVVERTENZE', 'ATTENZIONE', 'PERICOLO',
            'WARNING', 'CAUTION', 'DANGER', 'AVOID',
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
        
        # Controllo prodotti con varianti (es. "Dachziegel Light")
        words = text_clean.lower().split()
        if len(words) >= 2:
            # Controlla se la prima parola è un prodotto protetto
            first_word = words[0]
            if first_word in self.product_names:
                return True
            
            # Controlla se qualsiasi parola è un prodotto protetto
            for word in words:
                if word in self.product_names:
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
        Carica un glossario personalizzato da file con supporto migliorato
        
        Args:
            file_path: Path al file glossario
        """
        loaded_terms = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            # Formato: tipo:termine
                            if ':' in line:
                                term_type, term = line.split(':', 1)
                                term = term.strip()
                                term_type = term_type.strip().lower()
                                
                                if term_type == 'product':
                                    self.add_product_name(term)
                                    loaded_terms += 1
                                elif term_type in ['technical', 'material', 'certification', 'professional']:
                                    self.add_technical_term(term)
                                    loaded_terms += 1
                                else:
                                    print(f"Warning: Tipo termine sconosciuto '{term_type}' alla riga {line_num}")
                            else:
                                # Default: prodotto
                                self.add_product_name(line)
                                loaded_terms += 1
                        except ValueError as e:
                            print(f"Warning: Errore parsing riga {line_num}: {line} - {e}")
                            
            print(f"✅ Caricati {loaded_terms} termini protetti dal glossario")
            
        except FileNotFoundError:
            print(f"⚠️  Glossario non trovato: {file_path}")
        except Exception as e:
            print(f"❌ Errore caricamento glossario: {e}")
    
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


def load_project_glossary(project_path: str, domain: str = None) -> TranslationGlossary:
    """
    Carica glossario specifico per progetto con supporto domini
    
    Args:
        project_path: Path alla directory del progetto
        domain: Dominio specifico (safety, construction, technical)
        
    Returns:
        Istanza glossario configurata
    """
    import os
    
    glossary = TranslationGlossary()
    
    # 1. Carica glossario base del progetto
    base_glossary_files = [
        os.path.join(project_path, 'glossary.txt'),
        os.path.join(project_path, 'config', 'glossary.txt'),
        os.path.join(project_path, '.glossary'),
    ]
    
    glossary_loaded = False
    for file_path in base_glossary_files:
        if os.path.exists(file_path):
            print(f"📚 Caricamento glossario base: {file_path}")
            glossary.load_custom_glossary(file_path)
            glossary_loaded = True
            break
    
    # 2. Carica glossario specifico per dominio se specificato
    if domain:
        domain_files = [
            os.path.join(project_path, f'glossary_{domain}.txt'),
            os.path.join(project_path, 'config', f'glossary_{domain}.txt'),
        ]
        
        for file_path in domain_files:
            if os.path.exists(file_path):
                print(f"🎯 Caricamento glossario dominio '{domain}': {file_path}")
                glossary.load_custom_glossary(file_path)
                break
    
    # 3. Auto-detect dominio da nomi file IDML se non specificato
    if not domain and project_path:
        idml_files = [f for f in os.listdir(project_path) if f.lower().endswith('.idml')]
        detected_domain = _detect_domain_from_files(idml_files)
        
        if detected_domain:
            print(f"🔍 Dominio rilevato automaticamente: {detected_domain}")
            domain_file = os.path.join(project_path, f'glossary_{detected_domain}.txt')
            if os.path.exists(domain_file):
                glossary.load_custom_glossary(domain_file)
    
    if not glossary_loaded:
        print("⚠️  Nessun glossario trovato - usando solo termini predefiniti")
    
    return glossary


def _detect_domain_from_files(filenames: list) -> str:
    """Rileva automaticamente il dominio dai nomi dei file"""
    safety_keywords = ['safeguard', 'safety', 'sicurezza', 'anticaduta', 'protezione']
    construction_keywords = ['skyfix', 'riwega', 'dach', 'roof', 'tetto', 'construction']
    
    filename_text = ' '.join(filenames).lower()
    
    if any(keyword in filename_text for keyword in safety_keywords):
        return 'safety'
    elif any(keyword in filename_text for keyword in construction_keywords):
        return 'construction'
    
    return None


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