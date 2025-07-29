"""
Async Translator - Traduttore asincrono per massimizzare performance con OpenAI API
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple, Any
import time
from openai import AsyncOpenAI
import json
from translation_memory import TranslationMemory
import logging


logger = logging.getLogger(__name__)


class AsyncTranslator:
    """Traduttore asincrono con caching e parallelizzazione"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", 
                 max_concurrent: int = 5, use_cache: bool = True,
                 tm_path: Optional[str] = None):
        """
        Inizializza il traduttore asincrono
        
        Args:
            api_key: Chiave API OpenAI
            model: Modello da utilizzare
            max_concurrent: Numero massimo di richieste concorrenti
            use_cache: Se utilizzare la Translation Memory
            tm_path: Path del database TM (opzionale)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.use_cache = use_cache
        self.tm = TranslationMemory(tm_path) if use_cache else None
        
        # Statistiche
        self.stats = {
            'cache_hits': 0,
            'api_calls': 0,
            'total_time': 0,
            'tokens_used': 0
        }
        
    async def translate_texts_batch(self, texts: List[str], target_language: str,
                                  source_language: Optional[str] = None,
                                  context: Optional[str] = None,
                                  document_type: Optional[str] = None,
                                  glossary_version: Optional[str] = None) -> List[str]:
        """
        Traduce una lista di testi in modo asincrono con caching
        
        Args:
            texts: Lista di testi da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto della traduzione
            document_type: Tipo di documento
            glossary_version: Versione del glossario
            
        Returns:
            Lista di testi tradotti
        """
        if not texts:
            return []
            
        start_time = time.time()
        
        # Prepara i task di traduzione
        translation_tasks = []
        results = [None] * len(texts)
        
        for i, text in enumerate(texts):
            # Controlla cache se abilitata
            if self.use_cache and self.tm:
                cached = self.tm.get_exact_match(text, target_language, context, document_type)
                if cached:
                    results[i] = cached['target_text']
                    self.stats['cache_hits'] += 1
                    logger.debug(f"Cache hit per: {text[:50]}...")
                    continue
                    
            # Crea task asincrono per traduzione
            task = self._create_translation_task(
                i, text, target_language, source_language, context
            )
            translation_tasks.append(task)
            
        # Esegui traduzioni in parallelo
        if translation_tasks:
            completed_translations = await asyncio.gather(*translation_tasks)
            
            # Inserisci risultati e aggiorna cache
            for idx, translation in completed_translations:
                if translation:
                    results[idx] = translation
                    
                    # Aggiungi alla TM se abilitata
                    if self.use_cache and self.tm:
                        self.tm.add_translation(
                            texts[idx], translation, target_language,
                            source_language, context, document_type,
                            glossary_version, self.model
                        )
                        
        self.stats['total_time'] = time.time() - start_time
        return results
        
    async def _create_translation_task(self, index: int, text: str, 
                                     target_language: str,
                                     source_language: Optional[str],
                                     context: Optional[str]) -> Tuple[int, str]:
        """
        Crea un task di traduzione asincrono
        
        Args:
            index: Indice del testo nella lista originale
            text: Testo da tradurre
            target_language: Lingua target
            source_language: Lingua sorgente
            context: Contesto
            
        Returns:
            Tupla (indice, traduzione)
        """
        async with self.semaphore:  # Limita concorrenza
            try:
                translation = await self._translate_single_async(
                    text, target_language, source_language, context
                )
                return (index, translation)
            except Exception as e:
                logger.error(f"Errore nella traduzione di '{text[:50]}...': {e}")
                return (index, text)  # Ritorna originale in caso di errore
                
    async def _translate_single_async(self, text: str, target_language: str,
                                    source_language: Optional[str] = None,
                                    context: Optional[str] = None) -> str:
        """
        Traduce un singolo testo in modo asincrono
        
        Args:
            text: Testo da tradurre
            target_language: Lingua di destinazione
            source_language: Lingua di origine
            context: Contesto
            
        Returns:
            Testo tradotto
        """
        self.stats['api_calls'] += 1
        
        source_lang_text = f" from {source_language}" if source_language else ""
        
        messages = [{
            "role": "system",
            "content": f"You are a professional technical translator. Translate text{source_lang_text} to {target_language}. CRITICAL RULES: Keep exact formatting, preserve technical terms, never add explanatory text, replace 'pag.' with 'S.' for German, do not include translation markers like 'Übersetzung:' in output."
        }]
        
        if context:
            messages.append({
                "role": "system", 
                "content": f"Translation context: {context}"
            })
            
        messages.append({
            "role": "user",
            "content": f"Translate: {text}"
        })
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=len(text) * 2  # Stima conservativa
            )
            
            # Aggiorna statistiche token
            if hasattr(response, 'usage'):
                self.stats['tokens_used'] += response.usage.total_tokens
                
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Errore API OpenAI: {e}")
            raise
            
    async def translate_with_terminology(self, texts: List[str], 
                                       terminology: Dict[str, str],
                                       target_language: str,
                                       source_language: Optional[str] = None,
                                       context: Optional[str] = None) -> List[str]:
        """
        Traduce applicando terminologia specifica
        
        Args:
            texts: Testi da tradurre
            terminology: Dizionario termine -> traduzione
            target_language: Lingua target
            source_language: Lingua sorgente
            context: Contesto
            
        Returns:
            Lista di traduzioni
        """
        # Crea contesto arricchito con terminologia
        term_context = self._create_terminology_context(terminology, context)
        
        # Traduci con contesto arricchito
        translations = await self.translate_texts_batch(
            texts, target_language, source_language, term_context
        )
        
        # Post-processa per garantire uso della terminologia
        return [self._enforce_terminology(trans, terminology) for trans in translations]
        
    def _create_terminology_context(self, terminology: Dict[str, str], 
                                  base_context: Optional[str]) -> str:
        """
        Crea contesto arricchito con terminologia
        
        Args:
            terminology: Dizionario dei termini
            base_context: Contesto base
            
        Returns:
            Contesto arricchito
        """
        term_list = [f"{term} = {translation}" for term, translation in terminology.items()]
        term_context = f"MANDATORY TERMINOLOGY:\n" + "\n".join(term_list)
        
        if base_context:
            return f"{base_context}\n\n{term_context}"
        return term_context
        
    def _enforce_terminology(self, text: str, terminology: Dict[str, str]) -> str:
        """
        Applica forzatamente la terminologia al testo tradotto
        
        Args:
            text: Testo tradotto
            terminology: Terminologia da applicare
            
        Returns:
            Testo con terminologia corretta
        """
        import re
        
        # Ordina termini per lunghezza (prima i più lunghi)
        sorted_terms = sorted(terminology.items(), key=lambda x: len(x[0]), reverse=True)
        
        for term, translation in sorted_terms:
            # Usa word boundaries per evitare sostituzioni parziali
            pattern = r'\b' + re.escape(term) + r'\b'
            text = re.sub(pattern, translation, text, flags=re.IGNORECASE)
            
        return text
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sulle traduzioni
        
        Returns:
            Dizionario con statistiche
        """
        stats = self.stats.copy()
        
        if stats['api_calls'] > 0:
            stats['avg_time_per_call'] = stats['total_time'] / stats['api_calls']
            stats['cache_hit_rate'] = stats['cache_hits'] / (stats['cache_hits'] + stats['api_calls'])
        else:
            stats['avg_time_per_call'] = 0
            stats['cache_hit_rate'] = 0
            
        if self.tm:
            stats['tm_stats'] = self.tm.get_statistics()
            
        return stats
        
    async def optimize_batch_size(self, sample_texts: List[str], 
                                target_language: str) -> int:
        """
        Ottimizza la dimensione del batch basandosi su test di performance
        
        Args:
            sample_texts: Testi di esempio per test
            target_language: Lingua target
            
        Returns:
            Dimensione ottimale del batch
        """
        batch_sizes = [1, 3, 5, 10, 15]
        results = {}
        
        for size in batch_sizes:
            if size > len(sample_texts):
                continue
                
            # Test con diversi batch size
            test_texts = sample_texts[:size]
            start = time.time()
            
            await self.translate_texts_batch(test_texts, target_language)
            
            elapsed = time.time() - start
            results[size] = elapsed / size  # Tempo medio per testo
            
        # Trova il batch size con il tempo medio più basso
        optimal_size = min(results, key=results.get)
        logger.info(f"Batch size ottimale: {optimal_size} (tempo medio: {results[optimal_size]:.2f}s)")
        
        return optimal_size
        
    def close(self):
        """Chiude risorse"""
        if self.tm:
            self.tm.close()
            
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Funzione helper per uso sincrono
def translate_async(texts: List[str], api_key: str, target_language: str,
                   source_language: Optional[str] = None,
                   context: Optional[str] = None,
                   model: str = "gpt-3.5-turbo",
                   use_cache: bool = True,
                   max_concurrent: int = 5) -> List[str]:
    """
    Wrapper sincrono per traduzione asincrona
    
    Args:
        texts: Testi da tradurre
        api_key: Chiave API
        target_language: Lingua target
        source_language: Lingua sorgente
        context: Contesto
        model: Modello OpenAI
        use_cache: Usa Translation Memory
        max_concurrent: Richieste concorrenti max
        
    Returns:
        Lista di traduzioni
    """
    async def _translate():
        async with AsyncTranslator(api_key, model, max_concurrent, use_cache) as translator:
            return await translator.translate_texts_batch(
                texts, target_language, source_language, context
            )
            
    return asyncio.run(_translate())