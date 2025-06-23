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
                       context: Optional[str] = None) -> List[str]:
        """
        Traduce una lista di testi
        
        Args:
            texts: Lista di testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine (opzionale, auto-detect se None)
            context: Contesto aggiuntivo per migliorare la traduzione
            
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
                batch_translations = self._translate_batch(
                    batch, target_language, source_language, context
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
                        context: Optional[str] = None) -> List[str]:
        """
        Traduce un batch di testi
        
        Args:
            texts: Batch di testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto aggiuntivo
            
        Returns:
            Lista di testi tradotti
        """
        # Crea il prompt per la traduzione
        prompt = self._create_translation_prompt(
            texts, target_language, source_language, context
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
                                 context: Optional[str] = None) -> str:
        """
        Crea il prompt per la traduzione
        
        Args:
            texts: Testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto aggiuntivo
            
        Returns:
            Prompt formattato per l'API
        """
        source_lang_text = f" from {source_language}" if source_language else ""
        
        prompt = f"""Translate the following texts{source_lang_text} to {target_language}.

IMPORTANT INSTRUCTIONS:
- Maintain the exact same format and structure
- Keep any special characters or formatting
- Preserve the tone and style of the original text
- Return exactly {len(texts)} translations, one per line
- Each translation should correspond to the input text at the same position
- Do not add explanations or additional text
"""
        
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
                             context: Optional[str] = None) -> str:
        """
        Traduce un singolo testo
        
        Args:
            text: Testo da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto aggiuntivo
            
        Returns:
            Testo tradotto
        """
        translations = self.translate_texts([text], target_language, source_language, context)
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