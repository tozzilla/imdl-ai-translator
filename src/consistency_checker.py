"""
Consistency Checker - Verifica e garantisce consistenza nelle traduzioni
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import logging
from datetime import datetime
from translation_memory import TranslationMemory


logger = logging.getLogger(__name__)


class ConsistencyChecker:
    """Verifica la consistenza delle traduzioni e applica regole di standardizzazione"""
    
    def __init__(self, tm: Optional[TranslationMemory] = None):
        """
        Inizializza il consistency checker
        
        Args:
            tm: Translation Memory da utilizzare per verifiche
        """
        self.tm = tm or TranslationMemory()
        self.inconsistencies = []
        self.suggestions = {}
        
        # Regole predefinite per lingue comuni
        self.default_rules = {
            'it': {
                'punctuation': [
                    (r'(\w)"', r'\1"'),  # Virgolette italiane
                    (r'"(\w)', r'"\1'),
                    (r'(\d),(\d)', r'\1,\2'),  # Virgola decimale
                ],
                'capitalization': [
                    (r'^([a-z])', lambda m: m.group(1).upper()),  # Maiuscola iniziale
                ],
                'spacing': [
                    (r'\s+', ' '),  # Spazi multipli
                    (r'\s+([.,;:!?])', r'\1'),  # Spazio prima punteggiatura
                    (r'([.,;:!?])(\w)', r'\1 \2'),  # Spazio dopo punteggiatura
                ]
            },
            'de': {
                'punctuation': [
                    (r'(\w)"', r'\1"'),  # Virgolette tedesche
                    (r'"(\w)', r'„\1'),
                    (r'(\d)\.(\d{3})', r'\1.\2'),  # Separatore migliaia
                    (r'(\d),(\d)', r'\1,\2'),  # Virgola decimale
                ],
                'capitalization': [
                    (r'\b([a-z])(\w*)\b', self._german_noun_capitalization),
                ],
                'spacing': [
                    (r'\s+', ' '),
                    (r'\s+([.,;:!?])', r'\1'),
                    (r'([.,;:!?])(\w)', r'\1 \2'),
                ]
            },
            'en': {
                'punctuation': [
                    (r'(\w)"', r'\1"'),  # Virgolette inglesi
                    (r'"(\w)', r'"\1'),
                    (r'(\d),(\d{3})', r'\1,\2'),  # Separatore migliaia
                    (r'(\d)\.(\d)', r'\1.\2'),  # Punto decimale
                ],
                'capitalization': [
                    (r'^([a-z])', lambda m: m.group(1).upper()),
                    (r'(?:^|\.\s+)([a-z])', lambda m: m.group(0)[:-1] + m.group(1).upper()),
                ],
                'spacing': [
                    (r'\s+', ' '),
                    (r'\s+([.,;:!?])', r'\1'),
                    (r'([.,;:!?])(\w)', r'\1 \2'),
                ]
            }
        }
        
    def check_translations(self, source_texts: List[str], 
                         translations: List[str],
                         target_language: str,
                         source_language: Optional[str] = None) -> List[Dict]:
        """
        Verifica la consistenza delle traduzioni
        
        Args:
            source_texts: Testi originali
            translations: Traduzioni da verificare
            target_language: Lingua delle traduzioni
            source_language: Lingua dei testi originali
            
        Returns:
            Lista di problemi trovati
        """
        issues = []
        
        # 1. Verifica consistenza terminologica
        term_issues = self._check_terminology_consistency(translations)
        issues.extend(term_issues)
        
        # 2. Verifica numeri e dati tecnici
        data_issues = self._check_technical_data(source_texts, translations)
        issues.extend(data_issues)
        
        # 3. Verifica formattazione
        format_issues = self._check_formatting(source_texts, translations)
        issues.extend(format_issues)
        
        # 4. Verifica contro Translation Memory
        if self.tm:
            tm_issues = self._check_against_tm(source_texts, translations, target_language)
            issues.extend(tm_issues)
            
        # 5. Verifica lunghezza testo (importante per layout)
        length_issues = self._check_text_length(source_texts, translations, target_language)
        issues.extend(length_issues)
        
        self.inconsistencies = issues
        return issues
        
    def apply_consistency_rules(self, translations: List[str], 
                              target_language: str) -> List[str]:
        """
        Applica regole di consistenza alle traduzioni
        
        Args:
            translations: Traduzioni da correggere
            target_language: Lingua target
            
        Returns:
            Traduzioni corrette
        """
        corrected = []
        
        # Ottieni regole per la lingua
        if self.tm:
            custom_rules = self.tm.get_consistency_rules(target_language)
        else:
            custom_rules = []
            
        default_rules = self.default_rules.get(target_language, {})
        
        for translation in translations:
            corrected_text = translation
            
            # Applica regole predefinite
            for rule_type, rules in default_rules.items():
                for pattern, replacement in rules:
                    if callable(replacement):
                        corrected_text = re.sub(pattern, replacement, corrected_text)
                    else:
                        corrected_text = re.sub(pattern, replacement, corrected_text)
                        
            # Applica regole personalizzate
            for rule in custom_rules:
                try:
                    corrected_text = re.sub(rule['pattern'], rule['replacement'], corrected_text)
                except Exception as e:
                    logger.error(f"Errore nell'applicazione regola {rule['id']}: {e}")
                    
            corrected.append(corrected_text)
            
        return corrected
        
    def _check_terminology_consistency(self, translations: List[str]) -> List[Dict]:
        """
        Verifica che termini simili siano tradotti in modo consistente
        
        Args:
            translations: Lista di traduzioni
            
        Returns:
            Lista di inconsistenze trovate
        """
        issues = []
        
        # Estrai termini ricorrenti (parole di 3+ caratteri che appaiono 2+ volte)
        all_text = ' '.join(translations).lower()
        words = re.findall(r'\b\w{3,}\b', all_text)
        word_counts = Counter(words)
        frequent_terms = {word for word, count in word_counts.items() if count >= 2}
        
        # Verifica variazioni dei termini
        term_variations = defaultdict(set)
        
        for translation in translations:
            translation_lower = translation.lower()
            for term in frequent_terms:
                # Cerca variazioni del termine (maiuscole/minuscole, plurali)
                pattern = r'\b' + term[:4] + r'\w*\b'
                variations = re.findall(pattern, translation, re.IGNORECASE)
                term_variations[term].update(variations)
                
        # Segnala termini con troppe variazioni
        for base_term, variations in term_variations.items():
            if len(variations) > 2:
                issues.append({
                    'type': 'terminology_inconsistency',
                    'severity': 'warning',
                    'term': base_term,
                    'variations': list(variations),
                    'message': f"Termine '{base_term}' ha {len(variations)} variazioni: {', '.join(variations)}"
                })
                
        return issues
        
    def _check_technical_data(self, source_texts: List[str], 
                            translations: List[str]) -> List[Dict]:
        """
        Verifica che dati tecnici siano preservati correttamente
        
        Args:
            source_texts: Testi originali
            translations: Traduzioni
            
        Returns:
            Lista di problemi trovati
        """
        issues = []
        
        for i, (source, translation) in enumerate(zip(source_texts, translations)):
            # Estrai numeri dal source
            source_numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', source)
            translation_numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', translation)
            
            # Normalizza per confronto (ignora differenze virgola/punto)
            source_nums_normalized = [num.replace(',', '.') for num in source_numbers]
            trans_nums_normalized = [num.replace(',', '.') for num in translation_numbers]
            
            # Verifica numeri mancanti
            missing_numbers = set(source_nums_normalized) - set(trans_nums_normalized)
            if missing_numbers:
                issues.append({
                    'type': 'missing_numbers',
                    'severity': 'error',
                    'index': i,
                    'missing': list(missing_numbers),
                    'message': f"Numeri mancanti nella traduzione: {', '.join(missing_numbers)}"
                })
                
            # Verifica unità di misura
            units_pattern = r'\b\d+\s*(mm|cm|m|kg|kN|MPa|bar|°C|°F)\b'
            source_units = re.findall(units_pattern, source, re.IGNORECASE)
            trans_units = re.findall(units_pattern, translation, re.IGNORECASE)
            
            if len(source_units) != len(trans_units):
                issues.append({
                    'type': 'units_mismatch',
                    'severity': 'error',
                    'index': i,
                    'source_units': source_units,
                    'trans_units': trans_units,
                    'message': "Numero di unità di misura non corrisponde"
                })
                
        return issues
        
    def _check_formatting(self, source_texts: List[str], 
                         translations: List[str]) -> List[Dict]:
        """
        Verifica che la formattazione sia preservata
        
        Args:
            source_texts: Testi originali
            translations: Traduzioni
            
        Returns:
            Lista di problemi
        """
        issues = []
        
        for i, (source, translation) in enumerate(zip(source_texts, translations)):
            # Verifica parentesi bilanciate
            source_parens = source.count('(') - source.count(')')
            trans_parens = translation.count('(') - translation.count(')')
            
            if source_parens == 0 and trans_parens != 0:
                issues.append({
                    'type': 'unbalanced_parentheses',
                    'severity': 'warning',
                    'index': i,
                    'message': "Parentesi non bilanciate nella traduzione"
                })
                
            # Verifica punti elenco
            source_bullets = len(re.findall(r'^\s*[•\-\*]\s', source, re.MULTILINE))
            trans_bullets = len(re.findall(r'^\s*[•\-\*]\s', translation, re.MULTILINE))
            
            if source_bullets != trans_bullets:
                issues.append({
                    'type': 'bullet_mismatch',
                    'severity': 'warning',
                    'index': i,
                    'message': f"Numero punti elenco diverso: {source_bullets} vs {trans_bullets}"
                })
                
        return issues
        
    def _check_against_tm(self, source_texts: List[str], 
                         translations: List[str],
                         target_language: str) -> List[Dict]:
        """
        Verifica contro Translation Memory per inconsistenze
        
        Args:
            source_texts: Testi originali
            translations: Traduzioni
            target_language: Lingua target
            
        Returns:
            Lista di inconsistenze
        """
        issues = []
        
        for i, (source, translation) in enumerate(zip(source_texts, translations)):
            # Cerca match esatto nella TM
            tm_match = self.tm.get_exact_match(source, target_language)
            
            if tm_match and tm_match['target_text'] != translation:
                # Calcola similarità
                similarity = SequenceMatcher(None, tm_match['target_text'], translation).ratio()
                
                if similarity < 0.95:  # Differenze significative
                    issues.append({
                        'type': 'tm_inconsistency',
                        'severity': 'warning',
                        'index': i,
                        'tm_translation': tm_match['target_text'],
                        'current_translation': translation,
                        'similarity': similarity,
                        'message': f"Traduzione diversa da TM (similarità: {similarity:.2%})"
                    })
                    
                    # Suggerisci la traduzione dalla TM
                    self.suggestions[i] = tm_match['target_text']
                    
        return issues
        
    def _check_text_length(self, source_texts: List[str], 
                          translations: List[str],
                          target_language: str) -> List[Dict]:
        """
        Verifica lunghezza testo per problemi di layout
        
        Args:
            source_texts: Testi originali  
            translations: Traduzioni
            target_language: Lingua target
            
        Returns:
            Lista di avvertimenti
        """
        issues = []
        
        # Fattori di espansione tipici per lingua
        expansion_factors = {
            'de': 1.3,  # Tedesco tipicamente 30% più lungo
            'fr': 1.2,  # Francese 20% più lungo
            'es': 1.15,  # Spagnolo 15% più lungo
            'it': 1.1,   # Italiano 10% più lungo
            'ja': 0.8,   # Giapponese più compatto
            'zh': 0.7,   # Cinese più compatto
        }
        
        max_expansion = expansion_factors.get(target_language, 1.2)
        
        for i, (source, translation) in enumerate(zip(source_texts, translations)):
            length_ratio = len(translation) / len(source) if len(source) > 0 else 0
            
            if length_ratio > max_expansion * 1.1:  # 10% oltre il previsto
                issues.append({
                    'type': 'excessive_expansion',
                    'severity': 'info',
                    'index': i,
                    'source_length': len(source),
                    'translation_length': len(translation),
                    'ratio': length_ratio,
                    'message': f"Traduzione {length_ratio:.0%} più lunga dell'originale"
                })
            elif length_ratio < 0.5:  # Troppo corta
                issues.append({
                    'type': 'excessive_contraction',
                    'severity': 'warning',
                    'index': i,
                    'source_length': len(source),
                    'translation_length': len(translation),
                    'ratio': length_ratio,
                    'message': f"Traduzione solo {length_ratio:.0%} dell'originale"
                })
                
        return issues
        
    def _german_noun_capitalization(self, match):
        """
        Applica capitalizzazione tedesca ai sostantivi
        
        Args:
            match: Match regex
            
        Returns:
            Parola con capitalizzazione corretta
        """
        word = match.group(0)
        
        # Lista semplificata di articoli/preposizioni che NON sono sostantivi
        non_nouns = {
            'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen',
            'und', 'oder', 'aber', 'mit', 'von', 'zu', 'in', 'an', 'auf',
            'für', 'bei', 'nach', 'aus', 'um', 'als', 'wie', 'ist', 'sind',
            'wird', 'werden', 'hat', 'haben', 'kann', 'können', 'muss', 'müssen'
        }
        
        if word.lower() not in non_nouns and len(word) > 2:
            return word.capitalize()
        return word
        
    def generate_report(self) -> str:
        """
        Genera un report delle inconsistenze trovate
        
        Returns:
            Report in formato testo
        """
        if not self.inconsistencies:
            return "✅ Nessuna inconsistenza trovata nelle traduzioni."
            
        report = ["# Report Consistenza Traduzioni\n"]
        
        # Raggruppa per tipo
        by_type = defaultdict(list)
        for issue in self.inconsistencies:
            by_type[issue['type']].append(issue)
            
        # Conta per severità
        by_severity = Counter(issue['severity'] for issue in self.inconsistencies)
        
        report.append(f"## Riepilogo")
        report.append(f"- Errori: {by_severity.get('error', 0)}")
        report.append(f"- Avvertimenti: {by_severity.get('warning', 0)}")
        report.append(f"- Info: {by_severity.get('info', 0)}\n")
        
        # Dettagli per tipo
        for issue_type, issues in by_type.items():
            report.append(f"## {issue_type.replace('_', ' ').title()}")
            for issue in issues[:5]:  # Mostra max 5 per tipo
                report.append(f"- {issue['message']}")
            if len(issues) > 5:
                report.append(f"- ...e altri {len(issues) - 5}")
            report.append("")
            
        # Suggerimenti
        if self.suggestions:
            report.append("## Suggerimenti dalla Translation Memory")
            for idx, suggestion in list(self.suggestions.items())[:5]:
                report.append(f"- Testo {idx}: Considera '{suggestion[:50]}...'")
                
        return "\n".join(report)
        
    def export_issues(self, output_path: str):
        """
        Esporta le inconsistenze in formato JSON
        
        Args:
            output_path: Path del file di output
        """
        import json
        
        export_data = {
            'timestamp': str(datetime.now()),
            'total_issues': len(self.inconsistencies),
            'by_severity': dict(Counter(i['severity'] for i in self.inconsistencies)),
            'issues': self.inconsistencies,
            'suggestions': self.suggestions
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)