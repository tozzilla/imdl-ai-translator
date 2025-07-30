"""
Translator - Gestisce la traduzione del testo usando OpenAI API
"""

import time
from typing import List, Dict, Optional, Tuple
import openai
from openai import OpenAI


class Translator:
    """Classe per gestire le traduzioni usando OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Inizializza il traduttore
        
        Args:
            api_key: Chiave API di OpenAI
            model: Modello da utilizzare (default: gpt-3.5-turbo)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.rate_limit_delay = 1.0  # Secondi tra le richieste
        self.max_retries = 3
        self.max_tokens_per_request = 3000
        
    def translate_texts(self, texts: List[str], target_language: str, 
                       source_language: Optional[str] = None,
                       context: Optional[str] = None,
                       max_lengths: Optional[List[int]] = None,
                       compression_mode: str = 'normal') -> List[str]:
        """
        Traduce una lista di testi
        
        Args:
            texts: Lista di testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine (opzionale, auto-detect se None)
            context: Contesto aggiuntivo per migliorare la traduzione
            max_lengths: Lista lunghezze massime per ogni testo (overflow prevention)
            compression_mode: Modalità compressione ('normal', 'compact', 'ultra_compact')
            
        Returns:
            Lista di testi tradotti
        """
        if not texts:
            return []
            
        # Raggruppa i testi in batch per ottimizzare le chiamate API
        batches = self._create_batches(texts)
        all_translations = []
        
        for i, batch in enumerate(batches):
            print(f"Traduzione batch {i+1}/{len(batches)} ({len(batch)} testi)...")
            
            try:
                # Estrai max_lengths per questo batch se forniti
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
                if i < len(batches) - 1:  # Non aspettare dopo l'ultimo batch
                    time.sleep(self.rate_limit_delay)
                    
            except Exception as e:
                print(f"Errore nella traduzione del batch {i+1}: {e}")
                # In caso di errore, mantieni i testi originali per questo batch
                all_translations.extend(batch)
                
        return all_translations
    
    def _create_batches(self, texts: List[str]) -> List[List[str]]:
        """
        Crea batch di testi per ottimizzare le chiamate API
        
        Args:
            texts: Lista completa di testi
            
        Returns:
            Lista di batch (liste di testi)
        """
        batches = []
        current_batch = []
        current_tokens = 0
        
        for text in texts:
            # Stima approssimativa dei token (4 caratteri = 1 token)
            estimated_tokens = len(text) // 4 + 100  # +100 per il prompt
            
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
        """
        Traduce un batch di testi
        
        Args:
            texts: Batch di testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto aggiuntivo
            max_lengths: Lunghezze massime per overflow prevention
            compression_mode: Modalità compressione
            
        Returns:
            Lista di testi tradotti
        """
        # Crea il prompt per la traduzione
        prompt = self._create_translation_prompt(
            texts, target_language, source_language, context,
            max_lengths, compression_mode
        )
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Bassa temperatura per coerenza
                    max_tokens=4000
                )
                
                translated_content = response.choices[0].message.content
                return self._parse_translation_response(translated_content, len(texts))
                
            except Exception as e:
                print(f"Tentativo {attempt + 1} fallito: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff esponenziale
                else:
                    raise e
    
    def _create_translation_prompt(self, texts: List[str], target_language: str,
                                 source_language: Optional[str] = None,
                                 context: Optional[str] = None,
                                 max_lengths: Optional[List[int]] = None,
                                 compression_mode: str = 'normal') -> str:
        """
        Crea il prompt per la traduzione
        
        Args:
            texts: Testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto aggiuntivo
            max_lengths: Lunghezze massime per overflow prevention
            compression_mode: Modalità compressione
            
        Returns:
            Prompt formattato per l'API
        """
        source_lang_text = f" from {source_language}" if source_language else ""
        
        # Aggiungi istruzioni specifiche per compression mode
        compression_instructions = self._get_compression_instructions(compression_mode, target_language)
        
        # Aggiungi istruzioni per lunghezze massime se specificate
        length_instructions = ""
        if max_lengths:
            length_instructions = "\n\nLENGTH CONSTRAINTS (CRITICAL - DO NOT EXCEED):\n"
            for i, max_len in enumerate(max_lengths, 1):
                length_instructions += f"- Text {i}: Maximum {max_len} characters\n"
            length_instructions += "\nIf a translation would exceed its limit, use these strategies:\n"
            length_instructions += "- Use technical abbreviations (mm, cm, kg, etc.)\n"
            length_instructions += "- Remove non-essential words (articles, fillers)\n"
            length_instructions += "- Use more concise phrasing\n"
            length_instructions += "- Prioritize technical accuracy over natural flow\n"
        
        # Costruisci prompt base senza contaminazione linguistica
        prompt = f"""You are a professional technical translator. Translate the following texts{source_lang_text} to {target_language}.

CRITICAL TRANSLATION RULES:
- Translate ONLY the provided text segments
- Maintain exact same format and structure  
- Keep all special characters and formatting unchanged
- Preserve technical terminology precisely
- Return exactly {len(texts)} translations, numbered 1 to {len(texts)}
- Do NOT add explanations, notes, or extra text
- Do NOT include translation markers or metadata in output
- Keep technical terms, product names, and measurements unchanged"""

        # Aggiungi regole specifiche per lingua target (evita contaminazione crociata)
        if target_language.lower() in ['german', 'de', 'deutsch']:
            prompt += "\n- Replace 'pag.' with 'S.' for German page references"
        elif target_language.lower() in ['english', 'en']:
            prompt += "\n- Use standard English conventions (e.g., 'page' for page references)"
        elif target_language.lower() in ['french', 'fr', 'français']:
            prompt += "\n- Use standard French conventions (e.g., 'page' for page references)"
        elif target_language.lower() in ['spanish', 'es', 'español']:
            prompt += "\n- Use standard Spanish conventions (e.g., 'página' for page references)"
            
        prompt += f"\n{compression_instructions}{length_instructions}\n"
        
        if context:
            prompt += f"\nCONTEXT: {context}\n"
            
        prompt += "\nTEXTS TO TRANSLATE:\n"
        
        for i, text in enumerate(texts, 1):
            prompt += f"{i}. {text}\n"
            
        prompt += f"\nProvide {len(texts)} translations, numbered from 1 to {len(texts)}:"
        
        return prompt
    
    def _parse_translation_response(self, response: str, expected_count: int) -> List[str]:
        """
        Estrae le traduzioni dalla risposta dell'API
        
        Args:
            response: Risposta dell'API
            expected_count: Numero atteso di traduzioni
            
        Returns:
            Lista di traduzioni estratte
        """
        lines = response.strip().split('\n')
        translations = []
        
        import re
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Cerca solo linee che iniziano con numero seguito da punto o parentesi
            match = re.match(r'^\d+[.)]\s*(.+)', line)
            if match:
                translation = match.group(1).strip()
                if translation:
                    translations.append(translation)
                
        # Verifica che il numero di traduzioni sia corretto
        if len(translations) != expected_count:
            print(f"Warning: Attese {expected_count} traduzioni, ricevute {len(translations)}")
            
            # Aggiusta il numero di traduzioni
            if len(translations) < expected_count:
                # Aggiungi traduzioni mancanti (mantieni originale)
                translations.extend(["[TRADUZIONE MANCANTE]"] * (expected_count - len(translations)))
            else:
                # Tronca traduzioni in eccesso
                translations = translations[:expected_count]
                
        return translations
    
    def translate_single_text(self, text: str, target_language: str,
                             source_language: Optional[str] = None,
                             context: Optional[str] = None,
                             max_length: Optional[int] = None,
                             compression_mode: str = 'normal') -> str:
        """
        Traduce un singolo testo
        
        Args:
            text: Testo da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto aggiuntivo
            max_length: Lunghezza massima per overflow prevention
            compression_mode: Modalità compressione
            
        Returns:
            Testo tradotto
        """
        max_lengths = [max_length] if max_length else None
        translations = self.translate_texts([text], target_language, source_language, context, max_lengths, compression_mode)
        return translations[0] if translations else text
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Restituisce un dizionario delle lingue supportate
        
        Returns:
            Dizionario codice_lingua -> nome_lingua
        """
        return {
            'en': 'English',
            'it': 'Italian',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'no': 'Norwegian',
            'da': 'Danish',
            'fi': 'Finnish',
            'pl': 'Polish',
            'cs': 'Czech',
            'hu': 'Hungarian',
            'ro': 'Romanian',
            'bg': 'Bulgarian',
            'hr': 'Croatian',
            'sk': 'Slovak',
            'sl': 'Slovenian',
            'et': 'Estonian',
            'lv': 'Latvian',
            'lt': 'Lithuanian',
            'mt': 'Maltese',
            'el': 'Greek',
            'tr': 'Turkish',
            'he': 'Hebrew',
            'th': 'Thai',
            'vi': 'Vietnamese'
        }
    
    def estimate_cost(self, texts: List[str], target_language: str) -> Dict[str, float]:
        """
        Stima il costo della traduzione
        
        Args:
            texts: Testi da tradurre
            target_language: Lingua di destinazione
            
        Returns:
            Dizionario con stime di costo
        """
        total_chars = sum(len(text) for text in texts)
        estimated_input_tokens = total_chars // 4  # Approssimazione
        estimated_output_tokens = estimated_input_tokens  # Stima conservativa
        
        # Prezzi approssimativi per GPT-3.5-turbo (da aggiornare)
        input_cost_per_1k = 0.0015  # USD per 1K token
        output_cost_per_1k = 0.002   # USD per 1K token
        
        input_cost = (estimated_input_tokens / 1000) * input_cost_per_1k
        output_cost = (estimated_output_tokens / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return {
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_output_tokens': estimated_output_tokens,
            'estimated_input_cost_usd': input_cost,
            'estimated_output_cost_usd': output_cost,
            'estimated_total_cost_usd': total_cost
        }
    
    def _get_compression_instructions(self, compression_mode: str, target_language: str) -> str:
        """
        Genera istruzioni specifiche per modalità di compressione
        
        Args:
            compression_mode: Modalità compressione
            target_language: Lingua destinazione
            
        Returns:
            Stringa con istruzioni di compressione
        """
        if compression_mode == 'normal':
            return ""
        
        base_instructions = "\n\nCOMPRESSION MODE ACTIVE:"
        
        if compression_mode == 'compact':
            instructions = base_instructions + """
- Prioritize brevity while maintaining technical accuracy
- Use standard abbreviations when appropriate (mm, cm, kg, etc.)
- Remove unnecessary articles and filler words
- Use concise phrasing over natural flow when space is limited
- Maintain all technical terminology and safety information"""
            
        elif compression_mode == 'ultra_compact':
            instructions = base_instructions + """
- MAXIMUM COMPRESSION: Prioritize extreme brevity
- Use abbreviations extensively (Install. = Installation, Mont. = Montage)
- Remove all non-essential words (articles, conjunctions, fillers)
- Use telegraphic style while preserving meaning
- Convert long phrases to shorter equivalents
- Maintain critical safety and technical information only"""
            
        else:
            return ""
        
        # Aggiungi istruzioni specifiche per lingua
        if target_language == 'de':
            instructions += """
- Use German technical abbreviations: S. (Seite), Abb. (Abbildung), gem. (gemäß)
- Compound words for brevity where appropriate
- Remove redundant prepositions and articles"""
        
        return instructions