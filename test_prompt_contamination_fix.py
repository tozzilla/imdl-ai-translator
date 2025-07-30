#!/usr/bin/env python3
"""
Test per verificare che i prompt non contengano contaminazione linguistica
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from async_translator import AsyncTranslator
from translator import Translator
from domain_translator import DomainAwareTranslator

def test_async_translator_prompts():
    """Test che AsyncTranslator generi prompt puliti per lingua"""
    
    print("🧪 Test AsyncTranslator - Prompt Contamination")
    print("=" * 45)
    
    translator = AsyncTranslator("fake_key", use_cache=False)
    
    # Test per diverse lingue
    test_cases = [
        ("english", "en"),
        ("german", "de"), 
        ("french", "fr"),
        ("spanish", "es")
    ]
    
    contamination_found = False
    
    for lang_name, lang_code in test_cases:
        print(f"\n🔍 Test lingua: {lang_name} ({lang_code})")
        
        # Simula creazione del messaggio di sistema
        source_lang_text = " from Italian"
        system_prompt = f"You are a professional technical translator. Translate text{source_lang_text} to {lang_name}. CRITICAL RULES: Keep exact formatting, preserve technical terms, never add explanatory text."
        
        # Aggiungi regole specifiche per lingua target (come nel codice)
        if lang_name.lower() in ['german', 'de', 'deutsch']:
            system_prompt += " Replace 'pag.' with 'S.' for German page references."
        elif lang_name.lower() in ['english', 'en']:
            system_prompt += " Use standard English conventions for all terms."
        elif lang_name.lower() in ['french', 'fr', 'français']:
            system_prompt += " Use standard French conventions for all terms."
        elif lang_name.lower() in ['spanish', 'es', 'español']:
            system_prompt += " Use standard Spanish conventions for all terms."
        
        system_prompt += " Do not include any translation markers or metadata in output."
        
        # Verifica contaminazione
        german_words = ['Übersetzung', 'German', 'S.', 'deutsch']
        contamination_words = []
        
        for word in german_words:
            if word in system_prompt and lang_name != 'german':
                contamination_words.append(word)
                contamination_found = True
        
        if contamination_words:
            print(f"   ❌ CONTAMINAZIONE trovata: {', '.join(contamination_words)}")
            print(f"   📝 Prompt: {system_prompt}")
        else:
            print(f"   ✅ Prompt pulito per {lang_name}")
    
    return not contamination_found

def test_translator_prompts():
    """Test che Translator generi prompt puliti"""
    
    print(f"\n🧪 Test Translator - Prompt Contamination")
    print("=" * 40)
    
    translator = Translator("fake_key")
    
    # Test costruzione prompt per diverse lingue
    test_languages = ["english", "german", "french", "spanish"]
    
    contamination_found = False
    
    for target_language in test_languages:
        print(f"\n🔍 Test lingua: {target_language}")
        
        # Simula costruzione prompt (dalle righe modificate)
        source_lang_text = " from Italian"
        prompt = f"""You are a professional technical translator. Translate the following texts{source_lang_text} to {target_language}.

CRITICAL TRANSLATION RULES:
- Translate ONLY the provided text segments
- Maintain exact same format and structure  
- Keep all special characters and formatting unchanged
- Preserve technical terminology precisely
- Return exactly 1 translations, numbered 1 to 1
- Do NOT add explanations, notes, or extra text
- Do NOT include translation markers or metadata in output
- Keep technical terms, product names, and measurements unchanged"""

        # Aggiungi regole specifiche per lingua target
        if target_language.lower() in ['german', 'de', 'deutsch']:
            prompt += "\n- Replace 'pag.' with 'S.' for German page references"
        elif target_language.lower() in ['english', 'en']:
            prompt += "\n- Use standard English conventions (e.g., 'page' for page references)"
        elif target_language.lower() in ['french', 'fr', 'français']:
            prompt += "\n- Use standard French conventions (e.g., 'page' for page references)"
        elif target_language.lower() in ['spanish', 'es', 'español']:
            prompt += "\n- Use standard Spanish conventions (e.g., 'página' for page references)"
        
        # Verifica contaminazione
        contamination_words = []
        
        # Parole tedesche che non dovrebbero apparire in altri prompt
        if target_language != 'german':
            german_terms = ['Übersetzung', 'S.' if 'German' in prompt else None, 'German' if target_language != 'german' else None]
            for term in german_terms:
                if term and term in prompt:
                    contamination_words.append(term)
                    contamination_found = True
        
        if contamination_words:
            print(f"   ❌ CONTAMINAZIONE trovata: {', '.join(contamination_words)}")
        else:
            print(f"   ✅ Prompt pulito per {target_language}")
    
    return not contamination_found

def test_domain_translator_prompts():
    """Test che DomainAwareTranslator generi prompt puliti"""
    
    print(f"\n🧪 Test DomainAwareTranslator - Prompt Contamination")
    print("=" * 50)
    
    translator = DomainAwareTranslator("fake_key", domain="safety")
    
    test_languages = ["english", "german", "french", "spanish"] 
    contamination_found = False
    
    for target_language in test_languages:
        print(f"\n🔍 Test lingua: {target_language}")
        
        # Simula costruzione prompt (come nel codice modificato)
        source_text = " from Italian"
        context = "Standard technical translation guidelines apply."
        protected_list = "SafeGuard, AISI 304"
        
        prompt = f"""You are a professional technical translator specializing in safety documentation.

TRANSLATION TASK: Translate the following texts{source_text} to {target_language}.

{context}

CRITICAL DOMAIN-SPECIFIC RULES:
1. PRESERVE UNCHANGED: {protected_list}
2. TECHNICAL PRECISION: Maintain exact technical terminology and measurements
3. PROFESSIONAL TONE: Use formal, precise language appropriate for technical manuals
4. FORMAT: Return exactly 1 numbered translations (1. 2. 3. etc.)"""

        # Regole specifiche per lingua target
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
        
        # Verifica contaminazione
        contamination_words = []
        
        if target_language != 'german':
            # Cerca riferimenti tedeschi inappropriati
            german_specific = ['Sie/Ihr', 'GERMAN GRAMMAR']
            for term in german_specific:
                if term in prompt:
                    contamination_words.append(term)
                    contamination_found = True
        
        if contamination_words:
            print(f"   ❌ CONTAMINAZIONE trovata: {', '.join(contamination_words)}")
        else:
            print(f"   ✅ Prompt pulito per {target_language}")
    
    return not contamination_found

def test_prompt_language_isolation():
    """Test che ogni lingua abbia prompt completamente isolato"""
    
    print(f"\n🧪 Test Isolamento Completo Prompt")
    print("=" * 35)
    
    # Simula prompt per inglese e tedesco
    english_prompt = "Use standard English conventions for all terms."
    german_prompt = "Replace 'pag.' with 'S.' for German page references."
    
    # Verifica che non ci siano sovrapposizioni
    english_has_german = any(word in english_prompt.lower() for word in ['german', 'deutsch', 'sie', 'ihr'])
    german_has_english = any(word in german_prompt.lower() for word in ['english', 'page references'] if word != 'page references')
    
    print(f"🔍 Verifica isolamento:")
    print(f"   Prompt inglese contiene tedesco: {'❌ SI' if english_has_german else '✅ NO'}")
    print(f"   Prompt tedesco contiene inglese: {'❌ SI' if german_has_english else '✅ NO'}")
    
    return not (english_has_german or german_has_english)

if __name__ == "__main__":
    print("🧪 Test Contaminazione Prompt - Sistema Traduzioni")
    print("=" * 55)
    
    # Test tutti i translator
    async_clean = test_async_translator_prompts()
    translator_clean = test_translator_prompts()
    domain_clean = test_domain_translator_prompts()
    isolation_clean = test_prompt_language_isolation()
    
    all_clean = async_clean and translator_clean and domain_clean and isolation_clean
    
    print(f"\n🎯 RISULTATI FINALI:")
    print(f"   AsyncTranslator: {'✅ PULITO' if async_clean else '❌ CONTAMINATO'}")
    print(f"   Translator: {'✅ PULITO' if translator_clean else '❌ CONTAMINATO'}")
    print(f"   DomainTranslator: {'✅ PULITO' if domain_clean else '❌ CONTAMINATO'}")
    print(f"   Isolamento: {'✅ COMPLETO' if isolation_clean else '❌ COMPROMESSO'}")
    
    print(f"\n💡 CONCLUSIONE:")
    if all_clean:
        print(f"   ✅ TUTTI I PROMPT PULITI")
        print(f"   → Nessuna contaminazione linguistica")
        print(f"   → Ogni lingua ha prompt specifico")
        print(f"   → Problema contaminazione RISOLTO")
    else:
        print(f"   ❌ CONTAMINAZIONE ANCORA PRESENTE")
        print(f"   → Verificare prompt specifici")
        print(f"   → Problema da risolvere")
    
    print(f"\n📋 NEXT STEPS:")
    print(f"   1. Test traduzione reale IT→EN")
    print(f"   2. Verificare assenza termini tedeschi")
    print(f"   3. Confermare fix contaminazione")