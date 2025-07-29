"""
Enhanced Post Processor - Miglioramento avanzato qualità traduzioni
"""

import re
from typing import List, Dict, Tuple, Optional
import logging
from post_processor import TranslationPostProcessor

logger = logging.getLogger(__name__)


class EnhancedTranslationPostProcessor(TranslationPostProcessor):
    """Post-processor avanzato con correzioni specifiche per domini tecnici"""
    
    def __init__(self):
        """Inizializza con regole avanzate"""
        super().__init__()
        
        # Aggiungi regole avanzate per la qualità tedesca
        self.advanced_german_rules = [
            # === CONSISTENZA FORMALE (Sie/Ihr) ===
            # Converte forme informali in formali
            (r'\bDeine\b', 'Ihre'),
            (r'\bDeiner\b', 'Ihrer'), 
            (r'\bDeinen\b', 'Ihren'),
            (r'\bDeinem\b', 'Ihrem'),
            (r'\bDu\s+(?=kannst|sollst|musst|wirst|könnten)', 'Sie '),
            (r'\bkannst\b', 'können'),
            (r'\bsollst\b', 'sollen'),
            (r'\bmusst\b', 'müssen'),
            (r'\bwirst\b', 'werden'),
            
            # === CORREZIONI CAPITALIZZAZIONE TEDESCA ===
            # Rimuovi maiuscole eccessive mantenendo acronimi
            (r'\b([A-ZÄÖÜ]{3,})\b(?![A-Za-z])', self._fix_german_caps),
            
            # === RIMOZIONE ARTEFATTI TRADUZIONE ===
            (r'Übersetzung:\s*', ''),
            (r'Translation:\s*', ''),
            (r'Traduzione:\s*', ''),  
            (r'German:\s*', ''),
            (r'Deutsch:\s*', ''),
            (r'\[TRADUZIONE MANCANTE\]', '[Übersetzung fehlt]'),
            
            # === FRASI RESIDUE GPT ===
            (r'Bitte Geben Sie.*?\.', ''),
            (r'Please Provide.*?\.', ''),
            (r'The Text.*?\.', ''),
            (r'Here is.*?German.*?:', ''),
            (r'Hier ist.*?Übersetzung.*?:', ''),
            
            # === PREPOSIZIONI E ARTICOLI TEDESCHI ===
            (r'\bauf Der\b', 'auf der'),
            (r'\bin Der\b', 'in der'),
            (r'\bzu Der\b', 'zur'),
            (r'\bvon Der\b', 'von der'),
            (r'\bmit Der\b', 'mit der'),
            (r'\bfür Der\b', 'für die'),
            (r'\bdurch Der\b', 'durch die'),
            (r'\bum Der\b', 'um die'),
            
            # === TERMINOLOGIA SICUREZZA ===
            (r'\bPERICOLO\b', 'GEFAHR'),
            (r'\bATTENZIONE\b', 'ACHTUNG'),
            (r'\bAVVERTENZA\b', 'WARNUNG'),
            (r'\bEVITARE\b', 'VERMEIDEN'),
            
            # === CORREZIONI PAGINE (COMPLETE) ===
            # Pattern complessi con >> e range
            (r'>>\s*pag\.\s*(\d+)\s*-\s*pag\.\s*(\d+)', r'>> S. \1 - S. \2'),
            (r'pag\.\s*(\d+)\s*-\s*pag\.\s*(\d+)', r'S. \1 - S. \2'),
            # Pattern singoli  
            (r'\bpag\.(\d+)\.', r'S.\1.'),
            (r'\bpag\.\s*(\d+)', r'S. \1'),
            (r'\bpagina\s+(\d+)', r'Seite \1'),
            
            # === NUMERI E UNITÀ ===
            # Spazi corretti per unità tedesche
            (r'(\d+)\s*kN\b', r'\1 kN'),
            (r'(\d+)\s*mm\b', r'\1 mm'),
            (r'(\d+)\s*cm\b', r'\1 cm'),
            (r'(\d+)\s*m(?![m])\b', r'\1 m'),
            (r'(\d+)\s*kg\b', r'\1 kg'),
            (r'(\d+)\s*°C\b', r'\1 °C'),
            
            # === FRASI COMUNI MANUALI TECNICI ===
            (r'\bvedere figura\b', 'siehe Abbildung'),
            (r'\bcome mostrato\b', 'wie dargestellt'), 
            (r'\bsecondo le istruzioni\b', 'nach den Anweisungen'),
            (r'\bin base al tipo\b', 'je nach Typ'),
            (r'\bdurante il montaggio\b', 'während der Montage'),
            (r'\bprima dell\'uso\b', 'vor dem Gebrauch'),
        ]
        
        # Aggiunge le regole avanzate a quelle esistenti
        self.correction_rules['de'].extend(self.advanced_german_rules)
        
        # Parole che devono rimanere maiuscole (acronimi tecnici)
        self.protected_caps = {
            'CE', 'EN', 'DIN', 'ISO', 'UNI', 'DGUV', 'TÜV', 'PSA', 'EPI', 'DPI',
            'EPDM', 'TPO', 'PVC', 'PIB', 'PE', 'PP', 'PU', 'XLPE', 'NBR', 'SBR', 'PTFE',
            'RIWEGA', 'WÜRTH', 'HILTI', 'SIMPSON', 'FISCHER',
            'SKYFIX', 'SAFEGUARD', 'FALZ', 'MYRIAD', 'INFINITY',
            'XML', 'PDF', 'HTML', 'CSS', 'API', 'URL', 'HTTP', 'HTTPS'
        }
    
    def _fix_german_caps(self, match):
        """Corregge maiuscole eccessive in tedesco mantenendo acronimi"""
        word = match.group(1)
        
        # Mantieni acronimi e codici tecnici maiuscoli
        if word in self.protected_caps:
            return word
        
        # Se è tutto maiuscolo e più di 2 caratteri, probabilmente è errore
        if len(word) > 2 and word.isupper() and word not in self.protected_caps:
            # Converti in capitalizzazione normale tedesca
            return word.capitalize()
        
        return word
    
    def validate_german_consistency(self, translations: List[str]) -> Dict[str, List[str]]:
        """Valida la consistenza delle traduzioni tedesche"""
        issues = {
            'formality_mixing': [],
            'untranslated_italian': [],
            'wrong_capitalization': [], 
            'missing_translations': [],
            'translation_artifacts': []
        }
        
        # Pattern per rilevare problemi
        du_forms = re.compile(r'\b(du|deine?[mnrs]?|dir|dich)\b', re.IGNORECASE)
        sie_forms = re.compile(r'\b(sie|ihre?[mnrs]?|ihnen)\b', re.IGNORECASE)
        italian_words = re.compile(r'\b(installazione|sicurezza|protezione|montaggio|istruzioni|manuale)\b', re.IGNORECASE)
        wrong_caps = re.compile(r'\b[A-ZÄÖÜ]{3,}\b')
        artifacts = re.compile(r'(übersetzung:|translation:|please provide|the text)', re.IGNORECASE)
        
        for i, text in enumerate(translations):
            if not text or text.strip() == '':
                issues['missing_translations'].append(f"Testo {i+1}: vuoto")
                continue
            
            # Check formality mixing
            has_du = du_forms.search(text)
            has_sie = sie_forms.search(text)
            if has_du and has_sie:
                issues['formality_mixing'].append(f"Testo {i+1}: {text[:50]}...")
            
            # Check untranslated Italian
            italian_match = italian_words.search(text)
            if italian_match:
                issues['untranslated_italian'].append(f"Testo {i+1}: '{italian_match.group()}' in '{text[:50]}...'")
            
            # Check wrong capitalization (excluding protected terms)
            caps_matches = wrong_caps.findall(text)
            for caps_word in caps_matches:
                if caps_word not in self.protected_caps:
                    issues['wrong_capitalization'].append(f"Testo {i+1}: '{caps_word}' in '{text[:50]}...'")
            
            # Check translation artifacts
            if artifacts.search(text):
                issues['translation_artifacts'].append(f"Testo {i+1}: artefatti traduzione in '{text[:50]}...'")
        
        return issues
    
    def process_translations(self, translations: List[str], target_language: str) -> List[str]:
        """Process translations with enhanced quality checks"""
        
        # Prima applica post-processing base
        base_corrected = super().process_translations(translations, target_language)
        
        # Poi applica validazioni specifiche per tedesco
        if target_language == 'de':
            enhanced_corrected = []
            
            for text in base_corrected:
                # Applica correzioni specifiche aggiuntive
                enhanced_text = self._apply_german_specific_fixes(text)
                enhanced_corrected.append(enhanced_text)
            
            # Genera report qualità
            issues = self.validate_german_consistency(enhanced_corrected)
            total_issues = sum(len(issue_list) for issue_list in issues.values())
            
            if total_issues > 0:
                logger.warning(f"🔍 Rilevati {total_issues} problemi di qualità:")
                for issue_type, issue_list in issues.items():
                    if issue_list:
                        logger.warning(f"  - {issue_type}: {len(issue_list)} problemi")
            else:
                logger.info("✅ Nessun problema di qualità rilevato")
            
            return enhanced_corrected
        
        return base_corrected
    
    def _apply_german_specific_fixes(self, text: str) -> str:
        """Applica correzioni specifiche per qualità tedesca"""
        fixed = text
        
        # 1. Standardizza formality (tutto su Sie)
        fixed = self._standardize_german_formality(fixed)
        
        # 2. Correggi capitalizzazione
        fixed = self._fix_german_capitalization_complete(fixed)
        
        # 3. Rimuovi artefatti residui
        fixed = self._clean_translation_artifacts(fixed)
        
        # 4. Correggi spacing unità di misura
        fixed = self._fix_measurement_spacing(fixed)
        
        # 5. IMPORTANTE: Traduci parole italiane rimaste
        fixed = self._translate_remaining_italian_words(fixed)
        
        return fixed.strip()
    
    def _standardize_german_formality(self, text: str) -> str:
        """Standardizza su formale (Sie) per tutto il testo"""
        # Converti tutte le forme informali in formali
        fixes = {
            r'\bDu\b': 'Sie',
            r'\bdir\b': 'Ihnen',
            r'\bdich\b': 'Sie',
            r'\bDeine\b': 'Ihre',
            r'\bDeiner\b': 'Ihrer',
            r'\bDeinen\b': 'Ihren',
            r'\bDeinem\b': 'Ihrem',
            r'\bkannst\b': 'können',
            r'\bsollst\b': 'sollen',
            r'\bmusst\b': 'müssen',
            r'\bwirst\b': 'werden',
            r'\bbist\b': 'sind',
            r'\bhast\b': 'haben'
        }
        
        result = text
        for pattern, replacement in fixes.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _fix_german_capitalization_complete(self, text: str) -> str:
        """Corregge capitalizzazione tedesca completa"""
        # Trova parole con maiuscole eccessive
        words = text.split()
        fixed_words = []
        
        for word in words:
            # Mantieni acronimi protetti
            clean_word = re.sub(r'[^\w]', '', word)  # Rimuovi punteggiatura per check
            if clean_word in self.protected_caps:
                fixed_words.append(word)
            # Se è tutto maiuscolo e più di 2 caratteri
            elif len(clean_word) > 2 and clean_word.isupper():
                # Capitalizza solo la prima lettera
                fixed_word = word.lower().capitalize()
                fixed_words.append(fixed_word)
            else:
                fixed_words.append(word)
        
        return ' '.join(fixed_words)
    
    def _clean_translation_artifacts(self, text: str) -> str:
        """Rimuove artefatti di traduzione residui"""
        artifacts = [
            r'Übersetzung:\s*',
            r'Translation:\s*',
            r'Deutsch:\s*',
            r'German:\s*',
            r'Here is.*?:',
            r'Hier ist.*?:',
            r'Please.*?German.*?:',
            r'Bitte.*?Deutsch.*?:',
        ]
        
        cleaned = text
        for pattern in artifacts:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Rimuovi spazi multipli
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _fix_measurement_spacing(self, text: str) -> str:
        """Corregge spacing delle unità di misura"""
        # Pattern per unità con spazio corretto
        units = ['kN', 'mm', 'cm', 'm', 'kg', '°C', 'daN', 'Pa', 'MPa']
        
        result = text
        for unit in units:
            # Assicura spazio singolo tra numero e unità
            pattern = r'(\d+)\s*' + re.escape(unit) + r'\b'
            replacement = r'\1 ' + unit
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def _translate_remaining_italian_words(self, text: str) -> str:
        """Forza la traduzione di parole italiane comuni rimaste"""
        # Dizionario forzato per parole che spesso non vengono tradotte
        forced_translations = {
            # Parole in maiuscolo
            'EVITARE': 'VERMEIDEN',
            'LEGNO': 'HOLZ', 
            'CALCESTRUZZO': 'BETON',
            'ACCIAIO': 'STAHL',
            'METALLO': 'METALL',
            'PLASTICA': 'KUNSTSTOFF',
            'VETRO': 'GLAS',
            'INSTALLAZIONE': 'INSTALLATION',
            'MONTAGGIO': 'MONTAGE',
            'FISSAGGIO': 'BEFESTIGUNG',
            'SICUREZZA': 'SICHERHEIT',
            'PROTEZIONE': 'SCHUTZ',
            'ATTENZIONE': 'ACHTUNG',
            'PERICOLO': 'GEFAHR',
            'AVVERTENZA': 'WARNUNG',
            # Nuove parole da aggiungere
            'INDICE': 'INHALTSVERZEICHNIS',
            'INTRODUZIONE': 'EINFÜHRUNG',
            'AVVERTENZE': 'WARNHINWEISE',
            'MARCATURA': 'KENNZEICHNUNG',
            'ASSISTENZA': 'KUNDENDIENST',
            # Nuove parole aggiunte
            'FISSAGGI': 'BEFESTIGUNGEN',
            'CODICE': 'CODE',
            'PARTE': 'TEIL',
            'POSIZIONE': 'POSITION',
            'FINITURA': 'OBERFLÄCHENBEHANDLUNG',
            
            # Parole minuscole
            'evitare': 'vermeiden',
            'legno': 'Holz',
            'calcestruzzo': 'Beton', 
            'acciaio': 'Stahl',
            'metallo': 'Metall',
            'plastica': 'Kunststoff',
            'vetro': 'Glas',
            'installazione': 'Installation',
            'montaggio': 'Montage',
            'fissaggio': 'Befestigung',
            'sicurezza': 'Sicherheit',
            'protezione': 'Schutz',
            'attenzione': 'Achtung',
            'pericolo': 'Gefahr',
            'avvertenza': 'Warnung',
            # Nuove parole minuscole
            'indice': 'Inhaltsverzeichnis',
            'introduzione': 'Einführung',
            'avvertenze': 'Warnhinweise',
            'marcatura': 'Kennzeichnung',
            'assistenza': 'Kundendienst',
            # Nuove parole minuscole aggiunte
            'fissaggi': 'Befestigungen',
            'codice': 'Code',
            'parte': 'Teil',
            'posizione': 'Position',
            'finitura': 'Oberflächenbehandlung',
            
            # Altre parole problematiche
            'utilizzare': 'verwenden',
            'verificare': 'prüfen',
            'controllare': 'kontrollieren',
            'assicurare': 'sicherstellen',
            'seguire': 'folgen',
            'rispettare': 'beachten',
            'manuale': 'Handbuch',
            'istruzioni': 'Anweisungen',
            'sistema': 'System',
            'elemento': 'Element',
            'componente': 'Komponente',
            'dispositivo': 'Gerät',
            'struttura': 'Struktur',
            'superficie': 'Oberfläche',
            'materiale': 'Material',
            'prodotto': 'Produkt'
        }
        
        result = text
        
        # Applica traduzioni forzate con word boundaries per precisione
        for italian, german in forced_translations.items():
            # Usa word boundary per evitare sostituzioni parziali
            pattern = r'\b' + re.escape(italian) + r'\b'
            result = re.sub(pattern, german, result)
        
        # Gestione speciale per riferimenti pagina (non usano word boundary)
        # Pattern complessi con >> e range
        result = re.sub(r'>>\s*pag\.\s*(\d+)\s*-\s*pag\.\s*(\d+)', r'>> S. \1 - S. \2', result)
        result = re.sub(r'pag\.\s*(\d+)\s*-\s*pag\.\s*(\d+)', r'S. \1 - S. \2', result)
        # Pattern singoli  
        result = re.sub(r'\bpag\.(\d+)\.', r'S.\1.', result)
        result = re.sub(r'\bpag\.\s*(\d+)', r'S. \1', result)
        
        return result
    
    def generate_enhanced_quality_report(self, original_texts: List[str], 
                                       final_texts: List[str], 
                                       target_language: str) -> Dict:
        """Genera report qualità avanzato"""
        
        base_report = self.generate_quality_report(original_texts, final_texts, target_language)
        
        # Aggiungi analisi specifica per tedesco
        if target_language == 'de':
            consistency_issues = self.validate_german_consistency(final_texts)
            
            base_report.update({
                'consistency_issues': consistency_issues,
                'total_consistency_issues': sum(len(issues) for issues in consistency_issues.values()),
                'consistency_score': self._calculate_consistency_score(consistency_issues, len(final_texts)),
                'recommendations': self._generate_recommendations(consistency_issues)
            })
        
        return base_report
    
    def _calculate_consistency_score(self, issues: Dict, total_texts: int) -> float:
        """Calcola punteggio consistenza (0-1)"""
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        if total_texts == 0:
            return 1.0
        
        # Ogni problema riduce il punteggio
        penalty = total_issues / total_texts
        score = max(0.0, 1.0 - penalty)
        
        return round(score, 3)
    
    def _generate_recommendations(self, issues: Dict) -> List[str]:
        """Genera raccomandazioni per migliorare la qualità"""
        recommendations = []
        
        if issues['formality_mixing']:
            recommendations.append("Standardizzare l'uso di 'Sie' (formale) in tutto il documento")
        
        if issues['untranslated_italian']:
            recommendations.append("Rivedere e tradurre i termini italiani rimanenti")
        
        if issues['wrong_capitalization']:
            recommendations.append("Correggere la capitalizzazione secondo le regole tedesche")
        
        if issues['translation_artifacts']:
            recommendations.append("Rimuovere artefatti di traduzione residui")
        
        if issues['missing_translations']:
            recommendations.append("Completare le traduzioni mancanti")
        
        return recommendations
    
    def apply_overflow_corrections(self, translations: List[str], 
                                 max_lengths: Optional[List[int]] = None,
                                 target_language: str = 'de') -> List[str]:
        """
        Applica correzioni specifiche per overflow prevention
        
        Args:
            translations: Lista traduzioni da correggere
            max_lengths: Lunghezze massime desiderate
            target_language: Lingua di destinazione
            
        Returns:
            Lista traduzioni con correzioni overflow
        """
        if not max_lengths:
            return translations
        
        corrected_translations = []
        
        for i, (translation, max_length) in enumerate(zip(translations, max_lengths)):
            if len(translation) <= max_length:
                corrected_translations.append(translation)
                continue
            
            # Applica correzioni progressive per ridurre lunghezza
            corrected = translation
            
            # 1. Abbreviazioni tecniche aggressive
            corrected = self._apply_aggressive_abbreviations(corrected, target_language)
            
            # 2. Rimozione parole non essenziali
            corrected = self._remove_non_essential_words(corrected, target_language)
            
            # 3. Compattazione numeri e unità
            corrected = self._compact_measurements_aggressive(corrected)
            
            # 4. Riduzioni grammaticali
            corrected = self._apply_grammatical_reductions(corrected, target_language)
            
            # 5. Ultimo tentativo: troncamento intelligente
            if len(corrected) > max_length:
                corrected = self._intelligent_truncation(corrected, max_length)
            
            reduction = len(translation) - len(corrected)
            if reduction > 0:
                logger.info(f"📏 Testo {i+1}: ridotto di {reduction} caratteri ({len(translation)}→{len(corrected)})")
            
            corrected_translations.append(corrected)
        
        return corrected_translations
    
    def _apply_aggressive_abbreviations(self, text: str, target_language: str) -> str:
        """Applica abbreviazioni aggressive per overflow"""
        if target_language != 'de':
            return text
        
        # Abbreviazioni aggressive tedesche
        aggressive_abbrevs = {
            # Parole comuni
            'Abbildung': 'Abb.',
            'Tabelle': 'Tab.',
            'Seite': 'S.',
            'Kapitel': 'Kap.',
            'Paragraph': 'Par.',
            'Installation': 'Install.',
            'Montage': 'Mont.',
            'Kontrolle': 'Kontroll.',
            'Überprüfung': 'Überpr.',
            'Sicherheit': 'Sich.',
            'Anweisung': 'Anw.',
            'Anweisungen': 'Anw.',
            'Handbuch': 'Handb.',
            'Dokument': 'Dok.',
            'Material': 'Mat.',
            'System': 'Syst.',
            'Komponente': 'Komp.',
            'Element': 'Elem.',
            # Nuove abbreviazioni aggiunte
            'Befestigungen': 'Befest.',
            'Position': 'Pos.',
            'Oberflächenbehandlung': 'Oberfl.',
            'Kennzeichnung': 'Kennz.',
            'Kundendienst': 'Service',
            'Inhaltsverzeichnis': 'Inhalt',
            
            # Frasi comuni
            'zum Beispiel': 'z.B.',
            'das heißt': 'd.h.',
            'unter anderem': 'u.a.',
            'und so weiter': 'usw.',
            'beziehungsweise': 'bzw.',
            'gegebenenfalls': 'ggf.',
            'in der Regel': 'i.d.R.',
            'im Allgemeinen': 'i.A.',
            
            # Misure (più aggressive)
            'Millimeter': 'mm',
            'Zentimeter': 'cm',
            'Kilogramm': 'kg',
            'Gramm': 'g',
            'Kilonewton': 'kN',
            'Newton': 'N',
            
            # Direzioni e posizioni
            'oben': 'o.',
            'unten': 'u.',
            'links': 'l.',
            'rechts': 'r.',
            'vorne': 'v.',
            'hinten': 'h.',
        }
        
        result = text
        for full_form, abbrev in aggressive_abbrevs.items():
            result = re.sub(r'\b' + re.escape(full_form) + r'\b', abbrev, result)
        
        return result
    
    def _remove_non_essential_words(self, text: str, target_language: str) -> str:
        """Rimuove parole non essenziali per overflow"""
        if target_language != 'de':
            return text
        
        # Parole completamente removibili in contesto tecnico
        removable_words = {
            'auch', 'noch', 'bereits', 'schon', 'dann', 'danach',
            'dabei', 'hierzu', 'dazu', 'außerdem', 'zusätzlich',
            'entsprechend', 'jeweilig', 'jeweils', 'gegebenenfalls', 
            'eventuell', 'möglicherweise', 'gegebenenfalls',
            'normalerweise', 'üblicherweise', 'grundsätzlich',
            'selbstverständlich', 'natürlich', 'offensichtlich'
        }
        
        # Articoli e preposizioni riducibili
        reducible_patterns = [
            (r'\bder\s+', ''),  # Rimuovi articoli determinativi dove possibile
            (r'\bdie\s+', ''),
            (r'\bdas\s+', ''),
            (r'\beiner\s+', ''),
            (r'\beines\s+', ''),
            (r'\beinem\s+', ''),
            (r'\bzu\s+dem\b', 'zum'),
            (r'\bzu\s+der\b', 'zur'),
            (r'\bin\s+dem\b', 'im'),
            (r'\bvon\s+dem\b', 'vom'),
            (r'\ban\s+dem\b', 'am'),
        ]
        
        words = text.split()
        filtered_words = []
        
        # Rimuovi parole non essenziali
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word not in removable_words:
                filtered_words.append(word)
        
        result = ' '.join(filtered_words)
        
        # Applica riduzioni pattern
        for pattern, replacement in reducible_patterns:
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def _compact_measurements_aggressive(self, text: str) -> str:
        """Compattazione aggressiva misure e numeri"""
        result = text
        
        # Riduzioni numeriche aggressive
        aggressive_patterns = [
            # Range senza spazi
            (r'(\d+)\s*bis\s*(\d+)', r'\1-\2'),
            (r'(\d+)\s*-\s*(\d+)', r'\1-\2'),
            (r'von\s*(\d+)\s*bis\s*(\d+)', r'\1-\2'),
            (r'zwischen\s*(\d+)\s*und\s*(\d+)', r'\1-\2'),
            
            # Unità senza spazi dove appropriato
            (r'(\d+)\s*x\s*(\d+)', r'\1x\2'),
            (r'(\d+)\s*/\s*(\d+)', r'\1/\2'),
            (r'(\d+)\s*:\s*(\d+)', r'\1:\2'),
            
            # Frazioni e decimali
            (r'(\d+),(\d+)', r'\1.\2'),  # Virgola -> punto per brevità
            
            # Temperature e percentuali
            (r'(\d+)\s*Grad\s*Celsius', r'\1°C'),
            (r'(\d+)\s*Prozent', r'\1%'),
            (r'(\d+)\s*prozent', r'\1%'),
            
            # Compattazione estrema per unità
            (r'(\d+)\s*Millimeter', r'\1mm'),
            (r'(\d+)\s*Zentimeter', r'\1cm'),
            (r'(\d+)\s*Meter(?!\\w)', r'\1m'),
            (r'(\d+)\s*Kilogramm', r'\1kg'),
            (r'(\d+)\s*Gramm(?!\\w)', r'\1g'),
        ]
        
        for pattern, replacement in aggressive_patterns:
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def _apply_grammatical_reductions(self, text: str, target_language: str) -> str:
        """Applica riduzioni grammaticali per compattezza"""
        if target_language != 'de':
            return text
        
        result = text
        
        # Riduzioni grammaticali tedesche
        grammar_reductions = [
            # Costruzioni verbose -> concise
            (r'es\\s+ist\\s+notwendig,?\\s*', ''),
            (r'es\\s+ist\\s+wichtig,?\\s*', ''),
            (r'es\\s+ist\\s+erforderlich,?\\s*', ''),
            (r'stellen\\s+Sie\\s+sicher,\\s*dass', 'sicherstellen:'),
            (r'achten\\s+Sie\\s+darauf,\\s*dass', 'beachten:'),
            (r'sorgen\\s+Sie\\s+dafür,\\s*dass', 'sicherstellen:'),
            
            # Forme di cortesia ridotte
            (r'bitte\\s+beachten\\s+Sie', 'beachten'),
            (r'wir\\s+empfehlen\\s+Ihnen', 'empfohlen:'),
            (r'es\\s+wird\\s+empfohlen', 'empfohlen:'),
            (r'Sie\\s+sollten', 'sollten'),
            
            # Connettori ridotti
            (r'darüber\\s+hinaus', 'außerdem'),
            (r'zusätzlich\\s+dazu', 'zusätzlich'),
            (r'abgesehen\\s+davon', 'außerdem'),
            (r'im\\s+Hinblick\\s+auf', 'für'),
            (r'mit\\s+Bezug\\s+auf', 'bezüglich'),
            (r'in\\s+Bezug\\s+auf', 'bezüglich'),
            
            # Forme composte ridotte
            (r'sowohl\\s+(\\w+)\\s+als\\s+auch\\s+(\\w+)', r'\1 und \2'),
            (r'nicht\\s+nur\\s+(\\w+)\\s+sondern\\s+auch\\s+(\\w+)', r'\1 und \2'),
            (r'entweder\\s+(\\w+)\\s+oder\\s+(\\w+)', r'\1 oder \2'),
        ]
        
        for pattern, replacement in grammar_reductions:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Rimuovi spazi multipli e pulisci
        result = re.sub(r'\\s+', ' ', result).strip()
        
        return result
    
    def _intelligent_truncation(self, text: str, max_length: int) -> str:
        """Troncamento intelligente come ultima risorsa"""
        if len(text) <= max_length:
            return text
        
        # Prova a troncare a fine frase
        sentences = re.split(r'[.!?]', text)
        if len(sentences) > 1:
            truncated = sentences[0] + '.'
            if len(truncated) <= max_length:
                logger.warning(f"⚠️ Troncamento a fine frase: {len(text)} → {len(truncated)}")
                return truncated
        
        # Prova a troncare a fine parola
        words = text.split()
        truncated_words = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_length - 3:  # -3 per '...'
                truncated_words.append(word)
                current_length += len(word) + 1
            else:
                break
        
        if truncated_words:
            result = ' '.join(truncated_words) + '...'
            logger.warning(f"⚠️ Troncamento a fine parola: {len(text)} → {len(result)}")
            return result
        
        # Troncamento brutale (ultimo resort)
        result = text[:max_length-3] + '...'
        logger.warning(f"⚠️ Troncamento brutale: {len(text)} → {len(result)}")
        return result