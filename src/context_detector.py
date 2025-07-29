"""
Context Detector - Rileva automaticamente il tipo di documento e contesto per migliorare la traduzione
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import Counter


class DocumentContextDetector:
    """Rileva automaticamente il contesto del documento per ottimizzare la traduzione"""
    
    def __init__(self):
        """Inizializza il rilevatore di contesto"""
        
        # Definisci keyword per diversi domini/contesti
        self.context_keywords = {
            'safety_manual': {
                'keywords': [
                    # Italiano
                    'sicurezza', 'anticaduta', 'protezione', 'dispositivo', 'imbracatura',
                    'ancoraggi', 'dpi', 'caduta', 'installazione', 'montaggio', 'fissaggio',
                    'avvertenze', 'pericolo', 'rischio', 'normativa', 'certificazione',
                    
                    # Inglese
                    'safety', 'fall protection', 'harness', 'anchor', 'installation',
                    'mounting', 'warning', 'danger', 'risk', 'regulation', 'certification',
                    
                    # Tedesco
                    'sicherheit', 'absturzsicherung', 'gurt', 'anker', 'installation',
                    'montage', 'warnung', 'gefahr', 'risiko', 'norm', 'zertifizierung',
                    
                    # Termini tecnici comuni
                    'ce', 'en', 'din', 'iso', 'uiaa', 'kn', 'kg', 'mpa'
                ],
                'weight': 1.0
            },
            
            'construction_manual': {
                'keywords': [
                    # Materiali e strumenti
                    'cemento', 'calcestruzzo', 'acciaio', 'ferro', 'legno', 'metallo',
                    'trapano', 'vite', 'bullone', 'tassello', 'ancoraggio',
                    'concrete', 'steel', 'wood', 'metal', 'drill', 'screw', 'bolt',
                    'beton', 'stahl', 'holz', 'bohren', 'schraube', 'bolzen',
                    
                    # Processi
                    'costruzione', 'edificio', 'struttura', 'fondazione', 'parete',
                    'construction', 'building', 'structure', 'foundation', 'wall',
                    'bau', 'gebäude', 'struktur', 'fundament', 'wand'
                ],
                'weight': 0.8
            },
            
            'technical_specification': {
                'keywords': [
                    # Specifiche tecniche
                    'specifica', 'caratteristica', 'prestazione', 'capacità',
                    'dimensione', 'peso', 'resistenza', 'carico', 'pressione',
                    'specification', 'characteristic', 'performance', 'capacity',
                    'dimension', 'weight', 'resistance', 'load', 'pressure',
                    'spezifikation', 'eigenschaft', 'leistung', 'kapazität',
                    'abmessung', 'gewicht', 'widerstand', 'last', 'druck',
                    
                    # Unità di misura
                    'mm', 'cm', 'm', 'kg', 'kn', 'mpa', 'bar', 'hz', 'v', 'w'
                ],
                'weight': 0.7
            },
            
            'marketing_brochure': {
                'keywords': [
                    # Marketing
                    'innovativo', 'qualità', 'eccellenza', 'leader', 'migliore',
                    'soluzione', 'vantaggi', 'benefici', 'conveniente',
                    'innovative', 'quality', 'excellence', 'leader', 'best',
                    'solution', 'advantages', 'benefits', 'convenient',
                    'innovativ', 'qualität', 'exzellenz', 'führer', 'beste',
                    'lösung', 'vorteile', 'nutzen', 'günstig',
                    
                    # Call to action
                    'contatta', 'richiedi', 'scopri', 'scegli',
                    'contact', 'request', 'discover', 'choose',
                    'kontakt', 'anfrage', 'entdecken', 'wählen'
                ],
                'weight': 0.6
            }
        }
        
        # Template di contesto per la traduzione
        self.context_templates = {
            'safety_manual': {
                'description': 'Technical safety manual for fall protection systems',
                'terminology_notes': 'Use precise safety terminology. Maintain all safety warnings. Keep technical specifications exact.',
                'tone': 'formal, technical, safety-focused'
            },
            'construction_manual': {
                'description': 'Construction and installation manual',
                'terminology_notes': 'Use standard construction terminology. Maintain technical precision for tools and materials.',
                'tone': 'technical, instructional'
            },
            'technical_specification': {
                'description': 'Technical specifications document',
                'terminology_notes': 'Maintain all technical data, measurements, and specifications exactly. Use standard technical terminology.',
                'tone': 'formal, precise, technical'
            },
            'marketing_brochure': {
                'description': 'Marketing and promotional material',
                'terminology_notes': 'Maintain persuasive tone while adapting to target culture. Keep brand names unchanged.',
                'tone': 'persuasive, engaging, commercial'
            }
        }
    
    def detect_context(self, text_segments: List[Dict]) -> Tuple[str, float, Dict]:
        """
        Rileva il contesto del documento analizzando i segmenti di testo
        
        Args:
            text_segments: Lista di segmenti di testo estratti dal documento
            
        Returns:
            Tuple con (context_name, confidence_score, context_info)
        """
        if not text_segments:
            return 'generic', 0.0, {'description': 'Generic document', 'tone': 'neutral'}
        
        # Combina tutto il testo per l'analisi
        all_text = ' '.join([segment['original_text'].lower() for segment in text_segments])
        
        # Calcola punteggi per ogni contesto
        context_scores = {}
        
        for context_name, context_data in self.context_keywords.items():
            keywords = context_data['keywords']
            weight = context_data['weight']
            
            # Conta le occorrenze delle keyword
            keyword_count = 0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                keyword_count += len(re.findall(r'\b' + re.escape(keyword.lower()) + r'\b', all_text))
            
            # Calcola il punteggio normalizzato
            # Considera sia la frequenza che la varietà delle keyword trovate
            unique_keywords_found = sum(1 for kw in keywords if kw.lower() in all_text)
            keyword_variety_score = unique_keywords_found / total_keywords
            
            # Punteggio totale combinato
            frequency_score = min(keyword_count / len(text_segments), 1.0)  # Normalizza per lunghezza
            total_score = (frequency_score * 0.6 + keyword_variety_score * 0.4) * weight
            
            context_scores[context_name] = total_score
        
        # Trova il contesto con il punteggio più alto
        if context_scores:
            best_context = max(context_scores, key=context_scores.get)
            confidence = context_scores[best_context]
            
            # Soglia minima per considerare il contesto valido
            if confidence > 0.1:
                context_info = self.context_templates.get(best_context, {})
                return best_context, confidence, context_info
        
        # Fallback per contesto generico
        return 'generic', 0.0, {
            'description': 'Generic document', 
            'terminology_notes': 'Use standard terminology for the domain.',
            'tone': 'neutral, professional'
        }
    
    def create_context_prompt(self, context_name: str, context_info: Dict, 
                            custom_context: Optional[str] = None) -> str:
        """
        Crea un prompt di contesto per la traduzione
        
        Args:
            context_name: Nome del contesto rilevato
            context_info: Informazioni sul contesto
            custom_context: Contesto personalizzato fornito dall'utente
            
        Returns:
            Stringa con il prompt di contesto
        """
        if custom_context:
            return f"DOCUMENT CONTEXT: {custom_context}"
        
        context_prompt = f"DOCUMENT TYPE: {context_info.get('description', 'Document')}\n"
        
        if context_info.get('terminology_notes'):
            context_prompt += f"TERMINOLOGY: {context_info['terminology_notes']}\n"
        
        if context_info.get('tone'):
            context_prompt += f"TONE: {context_info['tone']}\n"
        
        return context_prompt.strip()
    
    def get_domain_specific_glossary_hints(self, context_name: str) -> List[str]:
        """
        Suggerisce termini specifici del dominio da aggiungere al glossario
        
        Args:
            context_name: Nome del contesto rilevato
            
        Returns:
            Lista di suggerimenti per il glossario
        """
        domain_suggestions = {
            'safety_manual': [
                'Add safety equipment names to glossary',
                'Include certification standards (CE, EN, DIN)',
                'Protect warning terms (DANGER, WARNING, CAUTION)',
                'Preserve technical specifications and load ratings'
            ],
            'construction_manual': [
                'Add tool names and materials to glossary',
                'Include measurement units and technical specifications',
                'Protect brand names of tools and materials',
                'Preserve installation steps numbering'
            ],
            'technical_specification': [
                'Protect all numerical values and units',
                'Add technical terms and standards to glossary',
                'Preserve model numbers and part codes',
                'Maintain technical drawings references'
            ],
            'marketing_brochure': [
                'Protect brand names and product names',
                'Add company-specific terminology to glossary',
                'Preserve contact information and URLs',
                'Maintain call-to-action formatting'
            ]
        }
        
        return domain_suggestions.get(context_name, [
            'Review document for domain-specific terms',
            'Add product names to glossary',
            'Protect technical specifications'
        ])


if __name__ == '__main__':
    # Test del rilevatore di contesto
    detector = DocumentContextDetector()
    
    # Simula segmenti di testo per test
    test_segments = [
        {'original_text': 'Dispositivo di protezione individuale anticaduta'},
        {'original_text': 'Installazione del sistema di sicurezza'},
        {'original_text': 'Avvertenze e istruzioni per l\'uso'},
        {'original_text': 'Certificazione CE secondo norma EN 361'},
        {'original_text': 'Carico di rottura: 22 kN'},
    ]
    
    context, confidence, info = detector.detect_context(test_segments)
    print(f"Contesto rilevato: {context}")
    print(f"Confidenza: {confidence:.2f}")
    print(f"Info: {info}")
    print()
    print("Prompt di contesto:")
    print(detector.create_context_prompt(context, info))