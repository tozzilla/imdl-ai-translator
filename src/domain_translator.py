"""
Domain-Aware Translator - Gestisce traduzioni specifiche per dominio
"""

import time
from typing import List, Dict, Optional
from openai import OpenAI
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.glossary import load_project_glossary
from overflow_detector import OverflowDetector, OverflowPrediction
from overflow_manager import OverflowManager


class DomainAwareTranslator:
    """Traduttore specializzato per domini specifici (sicurezza, costruzioni, etc.)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo", project_path: str = None, domain: str = None):
        """
        Inizializza il traduttore domain-aware
        
        Args:
            api_key: Chiave API OpenAI
            model: Modello da utilizzare
            project_path: Path del progetto per caricare glossario
            domain: Dominio specifico (safety, construction, technical)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.domain = domain
        self.project_path = project_path
        
        # Carica glossario specifico per dominio
        self.glossary = load_project_glossary(project_path or ".", domain)
        
        # NOTA: I context templates sono ora generati dinamicamente per lingua
        
        # Impostazioni traduzione
        self.rate_limit_delay = 1.0
        self.max_retries = 3
        self.max_tokens_per_request = 3000
        
        # Moduli per overflow prevention
        self.overflow_detector = OverflowDetector()
        self.overflow_manager = OverflowManager()
    
    def _get_safety_context(self, target_language: str = 'german') -> str:
        """Contesto specifico per manuali di sicurezza anticaduta"""
        base_context = """This is a SAFETY MANUAL for fall protection systems. 
Translation requirements:
- Maintain precise technical terminology for safety equipment
- Preserve all product names, model numbers, and certifications
- Keep regulatory references (EN, DIN, DGUV) unchanged
- Maintain imperative tone for safety instructions"""
        
        # Aggiungi requisiti specifici per lingua
        if target_language.lower() in ['german', 'de', 'deutsch']:
            base_context += "\n- Use formal German (Sie/Ihr) consistently throughout\n- Use standard German safety manual language and structure\n- Follow German industrial safety documentation standards"
        elif target_language.lower() in ['english', 'en']:
            base_context += "\n- Use formal, professional English throughout\n- Follow standard English safety manual conventions\n- Use clear, direct language appropriate for safety documentation"
        elif target_language.lower() in ['french', 'fr', 'français']:
            base_context += "\n- Use formal French (vous) consistently throughout\n- Follow French safety documentation standards\n- Maintain professional tone appropriate for technical safety manuals"
        elif target_language.lower() in ['spanish', 'es', 'español']:
            base_context += "\n- Use formal Spanish (usted) consistently throughout\n- Follow Spanish safety documentation conventions\n- Use professional language appropriate for industrial safety manuals"
        else:
            base_context += f"\n- Use formal, professional language appropriate for {target_language}\n- Follow standard {target_language} technical documentation conventions"
            
        return base_context
    
    def _get_construction_context(self, target_language: str = 'german') -> str:
        """Contesto specifico per settore edile/costruzioni"""
        base_context = """This is a CONSTRUCTION/BUILDING manual for roofing systems.
Translation requirements:
- Maintain precise technical terminology for building materials
- Preserve all product names, material specifications, and standards
- Keep building codes and standards (DIN, EN) unchanged
- Maintain technical precision for measurements and specifications"""
        
        # Aggiungi requisiti specifici per lingua
        if target_language.lower() in ['german', 'de', 'deutsch']:
            base_context += "\n- Use formal German (Sie/Ihr) for professional documentation\n- Use standard German construction industry language\n- Follow German building documentation conventions"
        elif target_language.lower() in ['english', 'en']:
            base_context += "\n- Use formal, professional English for documentation\n- Use standard English construction industry terminology\n- Follow English building documentation conventions"
        elif target_language.lower() in ['french', 'fr', 'français']:
            base_context += "\n- Use formal French (vous) for professional documentation\n- Use standard French construction industry language\n- Follow French building documentation conventions"
        elif target_language.lower() in ['spanish', 'es', 'español']:
            base_context += "\n- Use formal Spanish (usted) for professional documentation\n- Use standard Spanish construction industry language\n- Follow Spanish building documentation conventions"
        else:
            base_context += f"\n- Use formal, professional {target_language} for documentation\n- Use standard {target_language} construction industry terminology"
            
        return base_context
    
    def _get_technical_context(self, target_language: str = 'german') -> str:
        """Contesto generico tecnico"""
        base_context = """This is a technical installation manual.
Translation requirements:
- Maintain precise technical terminology
- Preserve all product names, model numbers, and certifications
- Keep measurements, specifications, and standards unchanged"""
        
        # Aggiungi requisiti specifici per lingua
        if target_language.lower() in ['german', 'de', 'deutsch']:
            base_context += "\n- Use formal German (Sie/Ihr) for professional documentation\n- Follow German technical documentation standards"
        elif target_language.lower() in ['english', 'en']:
            base_context += "\n- Use formal, professional English for documentation\n- Follow standard English technical documentation conventions"
        elif target_language.lower() in ['french', 'fr', 'français']:
            base_context += "\n- Use formal French (vous) for professional documentation\n- Follow French technical documentation standards"
        elif target_language.lower() in ['spanish', 'es', 'español']:
            base_context += "\n- Use formal Spanish (usted) for professional documentation\n- Follow Spanish technical documentation standards"
        else:
            base_context += f"\n- Use formal, professional {target_language} for documentation\n- Follow standard {target_language} technical documentation conventions"
            
        return base_context
    
    def _get_context_for_domain(self, domain: str, target_language: str) -> str:
        """Ottiene il contesto appropriato per dominio e lingua"""
        if domain == 'safety':
            return self._get_safety_context(target_language)
        elif domain == 'construction':
            return self._get_construction_context(target_language)
        elif domain == 'technical':
            return self._get_technical_context(target_language)
        else:
            # Default a contesto tecnico
            return self._get_technical_context(target_language)
    
    def translate_texts(self, texts: List[str], target_language: str, 
                       source_language: Optional[str] = None,
                       custom_context: Optional[str] = None,
                       frame_metrics: Optional[Dict] = None,
                       prevent_overflow: bool = False) -> List[str]:
        """
        Traduce testi con consapevolezza del dominio
        
        Args:
            texts: Lista di testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            custom_context: Contesto personalizzato (sovrascrive quello del dominio)
            frame_metrics: Metriche frame IDML per overflow prevention
            prevent_overflow: Attiva prevenzione overflow
            
        Returns:
            Lista di testi tradotti
        """
        if not texts:
            return []
        
        # Overflow prevention se richiesta
        max_lengths = None
        compression_mode = 'normal'
        
        if prevent_overflow:
            print("🔍 Analisi overflow prevention...")
            
            # Predici potenziali overflow
            overflow_predictions = self.overflow_detector.predict_translation_overflow(
                texts, target_language, frame_metrics or {}
            )
            
            # Genera report overflow
            overflow_report = self.overflow_detector.generate_overflow_report(
                overflow_predictions, target_language
            )
            
            print(f"📊 Rischio overflow medio: {overflow_report['summary']['average_overflow_risk']:.2f}")
            high_risk_count = overflow_report['risk_distribution']['high'] + overflow_report['risk_distribution']['critical']
            if high_risk_count > 0:
                print(f"⚠️ {high_risk_count} testi ad alto rischio overflow")
                compression_mode = 'compact' if high_risk_count < len(texts) * 0.3 else 'ultra_compact'
                print(f"🔧 Modalità compressione attivata: {compression_mode}")
            
            # Estrai lunghezze massime consigliate
            max_lengths = [pred.recommended_max_length for pred in overflow_predictions]
        
        # Determina il contesto da usare (ora dinamico per lingua)
        context = custom_context
        if not context:
            context = self._get_context_for_domain(self.domain, target_language)
        
        # Raggruppa i testi in batch
        batches = self._create_batches(texts)
        all_translations = []
        
        for i, batch in enumerate(batches):
            print(f"🔄 Traduzione batch {i+1}/{len(batches)} ({len(batch)} testi)...")
            
            try:
                # Estrai max_lengths per questo batch se disponibili
                batch_max_lengths = None
                if max_lengths:
                    start_idx = len(all_translations)
                    end_idx = start_idx + len(batch)
                    batch_max_lengths = max_lengths[start_idx:end_idx]
                
                batch_translations = self._translate_batch(
                    batch, target_language, source_language, context,
                    batch_max_lengths, compression_mode
                )
                all_translations.extend(batch_translations)
                
                # Rate limiting
                if i < len(batches) - 1:
                    time.sleep(self.rate_limit_delay)
                    
            except Exception as e:
                print(f"❌ Errore nella traduzione del batch {i+1}: {e}")
                # Fallback: mantieni testi originali
                all_translations.extend(batch)
        
        return all_translations
    
    def _create_batches(self, texts: List[str]) -> List[List[str]]:
        """Crea batch ottimizzati per le chiamate API"""
        batches = []
        current_batch = []
        current_tokens = 0
        
        for text in texts:
            estimated_tokens = len(text) // 4 + 200  # +200 per prompt domain-aware
            
            if current_tokens + estimated_tokens > self.max_tokens_per_request and current_batch:
                batches.append(current_batch)
                current_batch = [text]
                current_tokens = estimated_tokens
            else:
                current_batch.append(text)
                current_tokens += estimated_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _translate_batch(self, texts: List[str], target_language: str,
                        source_language: Optional[str] = None,
                        context: Optional[str] = None,
                        max_lengths: Optional[List[int]] = None,
                        compression_mode: str = 'normal') -> List[str]:
        """Traduce un singolo batch"""
        
        # Crea prompt domain-aware
        prompt = self._create_domain_prompt(
            texts, target_language, source_language, context,
            max_lengths, compression_mode
        )
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,  # Bassa temperatura per precisione tecnica
                    max_tokens=4000
                )
                
                translated_content = response.choices[0].message.content
                return self._parse_translation_response(translated_content, len(texts))
                
            except Exception as e:
                print(f"⚠️ Tentativo {attempt + 1} fallito: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e
    
    def _create_domain_prompt(self, texts: List[str], target_language: str,
                             source_language: Optional[str] = None,
                             context: Optional[str] = None,
                             max_lengths: Optional[List[int]] = None,
                             compression_mode: str = 'normal') -> str:
        """Crea prompt specializzato per dominio"""
        
        source_text = f" from {source_language}" if source_language else ""
        
        # Ottieni termini protetti per questo batch
        protected_terms = set()
        for text in texts:
            protected_terms.update(self.glossary.get_protected_terms_in_text(text))
        
        protected_list = ", ".join(protected_terms) if protected_terms else "None"
        
        # Aggiungi istruzioni per overflow prevention
        overflow_instructions = self._get_overflow_prevention_instructions(
            max_lengths, compression_mode, target_language
        )
        
        # Costruisci prompt senza contaminazione linguistica
        prompt = f"""You are a professional technical translator specializing in {self.domain or 'technical'} documentation.

TRANSLATION TASK: Translate the following texts{source_text} to {target_language}.

{context or "Standard technical translation guidelines apply."}

CRITICAL DOMAIN-SPECIFIC RULES:
1. PRESERVE UNCHANGED: {protected_list}
2. TECHNICAL PRECISION: Maintain exact technical terminology and measurements
3. PROFESSIONAL TONE: Use formal, precise language appropriate for technical manuals
4. FORMAT: Return exactly {len(texts)} numbered translations (1. 2. 3. etc.)"""

        # Regole specifiche per lingua target (evita contaminazione)
        if target_language.lower() in ['german', 'de', 'deutsch']:
            prompt += "\n5. CONSISTENCY: Use formal address (Sie/Ihr) consistently throughout ALL translations"
            prompt += "\n6. GERMAN GRAMMAR: Apply proper German capitalization rules (only first word and nouns)"
        elif target_language.lower() in ['english', 'en']:
            prompt += "\n5. CONSISTENCY: Use formal, professional language throughout"
            prompt += "\n6. ENGLISH GRAMMAR: Apply standard English capitalization and grammar rules"
        elif target_language.lower() in ['french', 'fr', 'français']:
            prompt += "\n5. CONSISTENCY: Use formal address (vous) consistently throughout"
            prompt += "\n6. FRENCH GRAMMAR: Apply proper French grammar and capitalization rules"
        elif target_language.lower() in ['spanish', 'es', 'español']:
            prompt += "\n5. CONSISTENCY: Use formal address (usted) consistently throughout"
            prompt += "\n6. SPANISH GRAMMAR: Apply proper Spanish grammar and capitalization rules"
        else:
            prompt += f"\n5. CONSISTENCY: Use formal, professional language appropriate for {target_language}"
            prompt += f"\n6. GRAMMAR: Apply standard {target_language} grammar and capitalization rules"
            
        prompt += f"""
{overflow_instructions}

PROTECTED TERMS IN THIS BATCH:
{protected_list}

TEXTS TO TRANSLATE:
"""
        
        for i, text in enumerate(texts, 1):
            # Aggiungi note sui termini protetti per ogni testo
            protected_note = self.glossary.create_protected_translation_note(text)
            if protected_note:
                prompt += f"{i}. [{protected_note}] {text}\\n"
            else:
                prompt += f"{i}. {text}\\n"
        
        prompt += f"""\\nProvide {len(texts)} professional technical translations, numbered 1 to {len(texts)}:"""
        
        return prompt
    
    def _parse_translation_response(self, response: str, expected_count: int) -> List[str]:
        """Estrae traduzioni dalla risposta API"""
        lines = response.strip().split('\\n')
        translations = []
        
        import re
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Cerca pattern numerati
            match = re.match(r'^(\\d+)[.)\\s]+(.+)', line)
            if match:
                translation = match.group(2).strip()
                
                # Rimuovi eventuali prefissi di traduzione residui
                translation = re.sub(r'^(Translation:|Traduzione:|Übersetzung:)\\s*', '', translation)
                
                if translation:
                    translations.append(translation)
        
        # Validazione numero traduzioni
        if len(translations) != expected_count:
            print(f"⚠️ Attese {expected_count} traduzioni, ricevute {len(translations)}")
            
            if len(translations) < expected_count:
                translations.extend(["[TRADUZIONE MANCANTE]"] * (expected_count - len(translations)))
            else:
                translations = translations[:expected_count]
        
        return translations
    
    def _get_overflow_prevention_instructions(self, max_lengths: Optional[List[int]], 
                                           compression_mode: str, 
                                           target_language: str) -> str:
        """Genera istruzioni per prevenzione overflow"""
        if not max_lengths and compression_mode == 'normal':
            return ""
        
        instructions = "\n\nOVERFLOW PREVENTION ACTIVE:"
        
        if max_lengths:
            instructions += "\n\nLENGTH CONSTRAINTS (CRITICAL - DO NOT EXCEED):"
            for i, max_len in enumerate(max_lengths, 1):
                instructions += f"\n- Text {i}: Maximum {max_len} characters"
            
            instructions += "\n\nLength reduction strategies (apply as needed):"
            instructions += "\n- Use technical abbreviations (mm, cm, kg, S. for Seite)"
            instructions += "\n- Remove non-essential articles and prepositions"
            instructions += "\n- Use compound words where appropriate (German)"
            instructions += "\n- Prioritize technical precision over natural flow"
        
        if compression_mode in ['compact', 'ultra_compact']:
            if compression_mode == 'compact':
                instructions += "\n\nCOMPACT MODE:"
                instructions += "\n- Favor brevity while maintaining technical accuracy"
                instructions += "\n- Use standard abbreviations for common terms"
                instructions += "\n- Remove redundant words and phrases"
            else:  # ultra_compact
                instructions += "\n\nULTRA-COMPACT MODE:"
                instructions += "\n- MAXIMUM compression required"
                instructions += "\n- Use telegraphic style with minimal words"
                instructions += "\n- Extensive use of technical abbreviations"
                instructions += "\n- Remove all non-essential language elements"
        
        # Aggiungi abbreviazioni tedesche specifiche
        if target_language == 'de':
            instructions += "\n\nGerman technical abbreviations to use:"
            instructions += "\n- Abb. (Abbildung), S. (Seite), gem. (gemäß)"
            instructions += "\n- Install. (Installation), Mont. (Montage)"
            instructions += "\n- verif. (verifizieren), kontroll. (kontrollieren)"
        
        return instructions
    
    def get_domain_info(self) -> Dict:
        """Restituisce informazioni sul dominio e glossario caricato"""
        return {
            'domain': self.domain,
            'project_path': self.project_path,
            'protected_terms_count': len(self.glossary.product_names) + len(self.glossary.technical_terms),
            'model': self.model,
            'overflow_prevention': True
        }