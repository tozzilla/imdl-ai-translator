"""
Post Processor - Corregge automaticamente errori comuni nelle traduzioni
"""

import re
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class TranslationPostProcessor:
    """Applica correzioni automatiche post-traduzione"""
    
    def __init__(self):
        """Inizializza il post-processor con regole di correzione"""
        
        # Regole di correzione per lingua
        self.correction_rules = {
            'de': [
                # Correzioni pagine
                (r'\bpag\.\s*(\d+)', r'S. \1'),
                (r'\bpagina\s+(\d+)', r'Seite \1'),
                
                # Rimozione frasi di traduzione errate
                (r'Übersetzung:\s*', ''),
                (r'Übersetzen:\s*', ''),
                (r'Bitte Geben Sie den.*?Möchten\.', ''),
                (r'Please Provide.*?German\.', ''),
                (r'The Text.*?Does', ''),
                
                # Correzioni mesi
                (r'\bGiugno\b', 'Juni'),
                (r'\bLuglio\b', 'Juli'),
                (r'\bAgosto\b', 'August'),
                (r'\bSettembre\b', 'September'),
                (r'\bOttobre\b', 'Oktober'),
                (r'\bNovembre\b', 'November'),
                (r'\bDicembre\b', 'Dezember'),
                (r'\bGennaio\b', 'Januar'),
                (r'\bFebbraio\b', 'Februar'),
                (r'\bMarzo\b', 'März'),
                (r'\bAprile\b', 'April'),
                (r'\bMaggio\b', 'Mai'),
                
                # Correzioni terminologia tecnica
                (r'\bInstallazione\b', 'Installation'),
                (r'\bSicurezza\b', 'Sicherheit'),
                (r'\bManuale\b', 'Handbuch'),
                (r'\bProtezione\b', 'Schutz'),
                (r'\bEdizione\b', 'Ausgabe'),
                
                # Materiali (maiuscolo e minuscolo)
                (r'\bLEGNO\b', 'HOLZ'),
                (r'\blegno\b', 'Holz'),
                (r'\bCALCESTRUZZO\b', 'BETON'),
                (r'\bcalcestruzzo\b', 'Beton'),
                (r'\bACCIAIO\b', 'STAHL'),
                (r'\bacciaio\b', 'Stahl'),
                
                # Verbi comuni
                (r'\bEVITARE\b', 'VERMEIDEN'),
                (r'\bevitare\b', 'vermeiden'),
                (r'\bVERIFICARE\b', 'PRÜFEN'),
                (r'\bverificare\b', 'prüfen'),
                (r'\bUTILIZZARE\b', 'VERWENDEN'),
                (r'\butilizzare\b', 'verwenden'),
                (r'\bSEGUIRE\b', 'FOLGEN'),
                (r'\bseguire\b', 'folgen'),
                
                # Preposizioni e articoli comuni
                (r'\bdella\b', 'der'),
                (r'\bdelle\b', 'der'),
                (r'\bdello\b', 'des'),
                (r'\bnegli\b', 'in den'),
                (r'\bnelle\b', 'in den'),
                (r'\bsulla\b', 'auf der'),
                (r'\bsulle\b', 'auf den'),
                (r'\bcon\b', 'mit'),
                (r'\bper\b', 'für'),
                (r'\buna\b', 'eine'),
                (r'\buno\b', 'ein'),
                (r'\bnel\b', 'im'),
                (r'\bnella\b', 'in der'),
                
                # Termini tecnici specifici
                (r'\bSISTEMA\b', 'SYSTEM'),
                (r'\bsistema\b', 'System'),
                (r'\bELEMENTI\b', 'ELEMENTE'),
                (r'\belementi\b', 'Elemente'),
                (r'\bDISPOSITIVO\b', 'GERÄT'),
                (r'\bdispositivo\b', 'Gerät'),
                (r'\bMONTAGGIO\b', 'MONTAGE'),
                (r'\bmontaggio\b', 'Montage'),
                (r'\bFISSAGGIO\b', 'BEFESTIGUNG'),
                (r'\bfissaggio\b', 'Befestigung'),
                (r'\bANCORAGGIO\b', 'VERANKERUNG'),
                (r'\bancoraggio\b', 'Verankerung'),
                
                # Rimozione inglese contaminante
                (r'\bPlease\b.*', ''),
                (r'\bProvide\b.*', ''),
                (r'\bText\b(?!\s+[a-z])', ''),  # Rimuovi "Text" standalone
                (r'\bFila\b', ''),  # Rimuovi errori "Fila"
                
                # Spazi multipli
                (r'\s+', ' '),
                (r'^\s+|\s+$', ''),  # Trim
            ],
            
            'it': [
                # Correzioni per italiano
                (r'\bS\.\s*(\d+)', r'pag. \1'),
                (r'\bSeite\s+(\d+)', r'pagina \1'),
                
                # Rimozione contaminazioni
                (r'Traduzione:\s*', ''),
                (r'Translation:\s*', ''),
                
                # Spazi
                (r'\s+', ' '),
                (r'^\s+|\s+$', ''),
            ],
            
            'en': [
                # Correzioni per inglese
                (r'\bpag\.\s*(\d+)', r'p. \1'),
                (r'\bpagina\s+(\d+)', r'page \1'),
                
                # DECONTAMINAZIONE: Rimuovi eventuali forzature tedesche
                (r'\bS\.\s*(\d+)', r'p. \1'),  # Converti riferimenti pagina tedeschi
                (r'\bSeite\s+(\d+)', r'page \1'),  # Converti "Seite" tedesco
                (r'\bSie\b', 'you'),  # Converti forma di cortesia tedesca
                (r'\bIhr\b', 'your'),  # Converti possessivo tedesco
                (r'\bÜbersetzung', 'Translation'),  # Converti "Traduzione" tedesco
                
                # Rimozione contaminazioni
                (r'Translation:\s*', ''),
                (r'Traduzione:\s*', ''),
                (r'German:\s*', ''),
                (r'Deutsch:\s*', ''),
                
                # Spazi
                (r'\s+', ' '),
                (r'^\s+|\s+$', ''),
            ],
            
            'fr': [
                # Correzioni per francese
                (r'\bpag\.\s*(\d+)', r'p. \1'),
                (r'\bpagina\s+(\d+)', r'page \1'),
                
                # DECONTAMINAZIONE: Rimuovi eventuali forzature tedesche
                (r'\bS\.\s*(\d+)', r'p. \1'),  # Converti riferimenti pagina tedeschi
                (r'\bSeite\s+(\d+)', r'page \1'),  # Converti "Seite" tedesco
                (r'\bSie\b', 'vous'),  # Converti forma di cortesia tedesca
                (r'\bIhr\b', 'votre'),  # Converti possessivo tedesco
                (r'\bÜbersetzung', 'Traduction'),  # Converti "Übersetzung" tedesco
                
                # Rimozione contaminazioni
                (r'Translation:\s*', ''),
                (r'Traduzione:\s*', ''),
                (r'German:\s*', ''),
                (r'Deutsch:\s*', ''),
                
                # Spazi
                (r'\s+', ' '),
                (r'^\s+|\s+$', ''),
            ],
            
            'es': [
                # Correzioni per spagnolo
                (r'\bpag\.\s*(\d+)', r'p. \1'),
                (r'\bpagina\s+(\d+)', r'página \1'),
                
                # DECONTAMINAZIONE: Rimuovi eventuali forzature tedesche
                (r'\bS\.\s*(\d+)', r'p. \1'),  # Converti riferimenti pagina tedeschi
                (r'\bSeite\s+(\d+)', r'página \1'),  # Converti "Seite" tedesco
                (r'\bSie\b', 'usted'),  # Converti forma di cortesia tedesca
                (r'\bIhr\b', 'su'),  # Converti possessivo tedesco
                (r'\bÜbersetzung', 'Traducción'),  # Converti "Übersetzung" tedesco
                
                # Rimozione contaminazioni
                (r'Translation:\s*', ''),
                (r'Traduzione:\s*', ''),
                (r'German:\s*', ''),
                (r'Deutsch:\s*', ''),
                
                # Spazi
                (r'\s+', ' '),
                (r'^\s+|\s+$', ''),
            ]
        }
        
        # Pattern per identificare traduzioni malformate
        self.malformed_patterns = [
            r'Bitte Geben Sie.*',
            r'Please Provide.*',
            r'The Text.*',
            r'Übersetzung:.*',
            r'Translation:.*',
            r'Traduzione:.*'
        ]
        
        # Nomi commerciali e prodotti che NON devono MAI essere tradotti
        self.protected_terms = {
            'SafeGuard Falz', 'SafeGuard Falz ZP',
            'SafeGuard Trapez', 'SafeGuard Trapez ZP', 'SafeGuard Metal Corner',
            'SafeGuard Trapez Single', 'SafeGuard Grip',
            'Control double X', 'Control single X',
            'SafeGuard Smart',
            'Skyfix-S', 'Skyfix-Z60', 'Skyfix-Z40', 'Skyfix-Z50',
            'SafeGuard Wall', 'SafeGuard Wall ZPC', 'SafeGuard Wall ZPT',
            'SafeGuard Corner C', 'SafeGuard Corner T',
            'Runner X',
            'SafeGuard Corda X'
        }
        
        # Dictionary completo di parole italiane comuni per identificazione automatica
        self.italian_words = {
            # Materiali
            'legno': 'Holz', 'LEGNO': 'HOLZ',
            'acciaio': 'Stahl', 'ACCIAIO': 'STAHL', 
            'calcestruzzo': 'Beton', 'CALCESTRUZZO': 'BETON',
            'metallo': 'Metall', 'METALLO': 'METALL',
            'plastica': 'Kunststoff', 'PLASTICA': 'KUNSTSTOFF',
            'vetro': 'Glas', 'VETRO': 'GLAS',
            
            # Verbi comuni
            'evitare': 'vermeiden', 'EVITARE': 'VERMEIDEN',
            'verificare': 'prüfen', 'VERIFICARE': 'PRÜFEN',
            'utilizzare': 'verwenden', 'UTILIZZARE': 'VERWENDEN',
            'seguire': 'folgen', 'SEGUIRE': 'FOLGEN',
            'installare': 'installieren', 'INSTALLARE': 'INSTALLIEREN',
            'montare': 'montieren', 'MONTARE': 'MONTIEREN',
            'fissare': 'befestigen', 'FISSARE': 'BEFESTIGEN',
            'controllare': 'kontrollieren', 'CONTROLLARE': 'KONTROLLIEREN',
            'assicurare': 'sicherstellen', 'ASSICURARE': 'SICHERSTELLEN',
            
            # Sostantivi tecnici
            'sistema': 'System', 'SISTEMA': 'SYSTEM',
            'elementi': 'Elemente', 'ELEMENTI': 'ELEMENTE',
            'elemento': 'Element', 'ELEMENTO': 'ELEMENT',
            'dispositivo': 'Gerät', 'DISPOSITIVO': 'GERÄT',
            'montaggio': 'Montage', 'MONTAGGIO': 'MONTAGE',
            'fissaggio': 'Befestigung', 'FISSAGGIO': 'BEFESTIGUNG',
            'ancoraggio': 'Verankerung', 'ANCORAGGIO': 'VERANKERUNG',
            'installazione': 'Installation', 'INSTALLAZIONE': 'INSTALLATION',
            'sicurezza': 'Sicherheit', 'SICUREZZA': 'SICHERHEIT',
            'protezione': 'Schutz', 'PROTEZIONE': 'SCHUTZ',
            'manuale': 'Handbuch', 'MANUALE': 'HANDBUCH',
            'istruzioni': 'Anweisungen', 'ISTRUZIONI': 'ANWEISUNGEN',
            'avvertenze': 'Warnungen', 'AVVERTENZE': 'WARNUNGEN',
            'attenzione': 'Achtung', 'ATTENZIONE': 'ACHTUNG',
            'pericolo': 'Gefahr', 'PERICOLO': 'GEFAHR',
            'caduta': 'Sturz', 'CADUTA': 'STURZ',
            'struttura': 'Struktur', 'STRUTTURA': 'STRUKTUR',
            'carico': 'Last', 'CARICO': 'LAST',
            'peso': 'Gewicht', 'PESO': 'GEWICHT',
            'resistenza': 'Widerstand', 'RESISTENZA': 'WIDERSTAND',
            'capacità': 'Kapazität', 'CAPACITÀ': 'KAPAZITÄT',
            
            # Preposizioni e articoli
            'della': 'der', 'delle': 'der', 'dello': 'des',
            'negli': 'in den', 'nelle': 'in den',
            'sulla': 'auf der', 'sulle': 'auf den',
            'con': 'mit', 'per': 'für',
            'una': 'eine', 'uno': 'ein',
            'nel': 'im', 'nella': 'in der',
            'dal': 'vom', 'dalla': 'von der',
            'alle': 'zu den', 'alla': 'zur',
            
            # Aggettivi comuni
            'corretto': 'korrekt', 'CORRETTO': 'KORREKT',
            'sicuro': 'sicher', 'SICURO': 'SICHER',
            'necessario': 'notwendig', 'NECESSARIO': 'NOTWENDIG',
            'importante': 'wichtig', 'IMPORTANTE': 'WICHTIG',
            'adatto': 'geeignet', 'ADATTO': 'GEEIGNET',
            'completo': 'vollständig', 'COMPLETO': 'VOLLSTÄNDIG',
            'minimo': 'minimal', 'MINIMO': 'MINIMAL',
            'massimo': 'maximal', 'MASSIMO': 'MAXIMAL',
            
            # Termini generali
            'edizione': 'Ausgabe', 'EDIZIONE': 'AUSGABE',
            'versione': 'Version', 'VERSIONE': 'VERSION',
            'numero': 'Nummer', 'NUMERO': 'NUMMER',
            'codice': 'Code', 'CODICE': 'CODE',
            'tipo': 'Typ', 'TIPO': 'TYP',
            'modello': 'Modell', 'MODELLO': 'MODELL',
            'serie': 'Serie', 'SERIE': 'SERIE',
            'dimensione': 'Abmessung', 'DIMENSIONE': 'ABMESSUNG',
            'dimensioni': 'Abmessungen', 'DIMENSIONI': 'ABMESSUNGEN',
            'misura': 'Maß', 'MISURA': 'MASS',
            'lunghezza': 'Länge', 'LUNGHEZZA': 'LÄNGE',
            'larghezza': 'Breite', 'LARGHEZZA': 'BREITE',
            'altezza': 'Höhe', 'ALTEZZA': 'HÖHE',
            'spessore': 'Dicke', 'SPESSORE': 'DICKE',
            'diametro': 'Durchmesser', 'DIAMETRO': 'DURCHMESSER',
            
            # Termini aggiuntivi sempre da tradurre
            'posizione': 'Position', 'POSIZIONE': 'POSITION',
            'codice': 'Code', 'CODICE': 'CODE', 
            'parte': 'Teil', 'PARTE': 'TEIL',
            'materiale': 'Material', 'MATERIALE': 'MATERIAL',
            'finitura': 'Ausführung', 'FINITURA': 'AUSFÜHRUNG',
        }
        
    def process_translations(self, translations: List[str], target_language: str) -> List[str]:
        """
        Applica post-processing alle traduzioni
        
        Args:
            translations: Lista di traduzioni da correggere
            target_language: Lingua target per applicare regole specifiche
            
        Returns:
            Lista di traduzioni corrette
        """
        # Mappa nomi lingue completi a codici
        language_mapping = {
            'english': 'en',
            'german': 'de', 
            'deutsch': 'de',
            'french': 'fr',
            'français': 'fr',
            'spanish': 'es',
            'español': 'es',
            'italian': 'it',
            'italiano': 'it'
        }
        
        # Converti nome lingua se necessario
        lang_code = language_mapping.get(target_language.lower(), target_language)
        
        if lang_code not in self.correction_rules:
            logger.warning(f"Nessuna regola di post-processing per lingua: {target_language} ({lang_code})")
            return translations
            
        corrected = []
        rules = self.correction_rules[lang_code]
        
        for i, translation in enumerate(translations):
            corrected_text = self._apply_corrections(translation, rules)
            
            # Applica correzioni automatiche per parole italiane se target è tedesco
            if target_language == 'de':
                corrected_text = self._fix_italian_words(corrected_text)
            
            # Verifica se la traduzione è malformata
            if self._is_malformed_translation(corrected_text):
                logger.warning(f"Traduzione malformata rilevata al segmento {i}: {corrected_text[:50]}...")
                # In caso di traduzione malformata, mantieni l'originale o applica fallback
                corrected_text = self._fallback_correction(translation)
                
            corrected.append(corrected_text)
            
        return corrected
        
    def _apply_corrections(self, text: str, rules: List[Tuple[str, str]]) -> str:
        """
        Applica le regole di correzione al testo, preservando i nomi commerciali protetti
        
        Args:
            text: Testo da correggere
            rules: Lista di tuple (pattern, replacement)
            
        Returns:
            Testo corretto
        """
        corrected = text
        
        # Prima salva i termini protetti sostituendoli con placeholder temporanei
        protected_placeholders = {}
        for i, protected_term in enumerate(self.protected_terms):
            placeholder = f"__PROTECTED_{i}__"
            if protected_term in corrected:
                protected_placeholders[placeholder] = protected_term
                corrected = corrected.replace(protected_term, placeholder)
        
        # Applica le regole di correzione
        for pattern, replacement in rules:
            try:
                corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
            except Exception as e:
                logger.error(f"Errore nell'applicazione regola {pattern}: {e}")
        
        # Ripristina i termini protetti
        for placeholder, protected_term in protected_placeholders.items():
            corrected = corrected.replace(placeholder, protected_term)
                
        return corrected.strip()
        
    def _fix_italian_words(self, text: str) -> str:
        """
        Corregge automaticamente parole italiane rimaste nel testo tedesco,
        preservando i nomi commerciali protetti
        
        Args:
            text: Testo da correggere
            
        Returns:
            Testo con parole italiane corrette in tedesco
        """
        corrected = text
        
        # Prima salva i termini protetti sostituendoli con placeholder temporanei
        protected_placeholders = {}
        for i, protected_term in enumerate(self.protected_terms):
            placeholder = f"__PROTECTED_{i}__"
            if protected_term in corrected:
                protected_placeholders[placeholder] = protected_term
                corrected = corrected.replace(protected_term, placeholder)
        
        # Applica correzioni word-by-word dal dizionario
        for italian_word, german_word in self.italian_words.items():
            # Usa word boundary per evitare sostituzioni parziali
            pattern = r'\b' + re.escape(italian_word) + r'\b'
            corrected = re.sub(pattern, german_word, corrected)
        
        # Ripristina i termini protetti
        for placeholder, protected_term in protected_placeholders.items():
            corrected = corrected.replace(placeholder, protected_term)
            
        return corrected
        
    def _is_malformed_translation(self, text: str) -> bool:
        """
        Verifica se una traduzione è malformata
        
        Args:
            text: Testo da verificare
            
        Returns:
            True se la traduzione è malformata
        """
        for pattern in self.malformed_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        # Verifica altre condizioni
        if len(text.strip()) == 0:
            return True
            
        # Verifica se contiene troppo inglese (per traduzioni in tedesco)
        english_words = ['please', 'provide', 'text', 'the', 'you', 'would', 'like', 'have']
        word_count = len(text.split())
        english_count = sum(1 for word in text.lower().split() if word in english_words)
        
        if word_count > 3 and english_count / word_count > 0.3:
            return True
            
        return False
        
    def _fallback_correction(self, original_text: str) -> str:
        """
        Applica correzione di fallback per traduzioni malformate
        
        Args:
            original_text: Testo originale
            
        Returns:
            Testo corretto con fallback
        """
        # In caso di fallimento, rimuovi i pattern più comuni
        fallback = original_text
        
        # Rimuovi frasi problematiche
        for pattern in self.malformed_patterns:
            fallback = re.sub(pattern, '', fallback, flags=re.IGNORECASE)
            
        # Pulizia finale
        fallback = re.sub(r'\s+', ' ', fallback).strip()
        
        return fallback if fallback else "[TRADUZIONE NON DISPONIBILE]"
        
    def get_quality_score(self, translations: List[str], target_language: str) -> float:
        """
        Calcola un punteggio di qualità per le traduzioni
        
        Args:
            translations: Lista di traduzioni
            target_language: Lingua target
            
        Returns:
            Punteggio di qualità (0-1)
        """
        if not translations:
            return 0.0
            
        issues = 0
        total = len(translations)
        
        for translation in translations:
            if self._is_malformed_translation(translation):
                issues += 1
                
        quality = 1 - (issues / total)
        return max(0.0, min(1.0, quality))
        
    def generate_quality_report(self, original_translations: List[str], 
                              corrected_translations: List[str],
                              target_language: str) -> Dict:
        """
        Genera un report sulla qualità delle traduzioni
        
        Args:
            original_translations: Traduzioni originali
            corrected_translations: Traduzioni corrette
            target_language: Lingua target
            
        Returns:
            Dizionario con report di qualità
        """
        original_quality = self.get_quality_score(original_translations, target_language)
        corrected_quality = self.get_quality_score(corrected_translations, target_language)
        
        # Conta correzioni applicate
        corrections_applied = 0
        for orig, corr in zip(original_translations, corrected_translations):
            if orig != corr:
                corrections_applied += 1
                
        return {
            'original_quality': original_quality,
            'corrected_quality': corrected_quality,
            'improvement': corrected_quality - original_quality,
            'corrections_applied': corrections_applied,
            'total_translations': len(original_translations),
            'correction_rate': corrections_applied / len(original_translations) if original_translations else 0
        }