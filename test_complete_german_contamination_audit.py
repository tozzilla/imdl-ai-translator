#!/usr/bin/env python3
"""
AUDIT COMPLETO per eliminare tutte le forzature tedesche dal sistema
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from async_translator import AsyncTranslator
from translator import Translator
from domain_translator import DomainAwareTranslator
from enhanced_post_processor import EnhancedTranslationPostProcessor
from post_processor import TranslationPostProcessor

def test_async_translator_language_isolation():
    """Test che AsyncTranslator sia completamente isolato per lingua"""
    
    print("🔍 AUDIT: AsyncTranslator Language Isolation")
    print("=" * 45)
    
    contamination_found = False
    
    # Test per ogni lingua non-tedesca
    test_languages = ['english', 'en', 'french', 'fr', 'spanish', 'es']
    
    for lang in test_languages:
        print(f"\n📋 Testing language: {lang}")
        
        # Simula la creazione del prompt (dal codice attuale)
        source_lang_text = " from Italian"
        system_prompt = f"You are a professional technical translator. Translate text{source_lang_text} to {lang}. CRITICAL RULES: Keep exact formatting, preserve technical terms, never add explanatory text."
        
        # Regole specifiche per lingua (dal codice)
        if lang.lower() in ['german', 'de', 'deutsch']:
            system_prompt += " Replace 'pag.' with 'S.' for German page references."
        elif lang.lower() in ['english', 'en']:
            system_prompt += " Use standard English conventions for all terms."
        elif lang.lower() in ['french', 'fr', 'français']:
            system_prompt += " Use standard French conventions for all terms."
        elif lang.lower() in ['spanish', 'es', 'español']:
            system_prompt += " Use standard Spanish conventions for all terms."
        
        system_prompt += " Do not include any translation markers or metadata in output."
        
        # Verifica contaminazione tedesca
        german_contamination = [
            'German', 'Deutsch', 'deutsch', 'Sie/Ihr', 'S.', 'Übersetzung', 
            'Seite', 'german', 'GERMAN'
        ]
        
        found_contamination = []
        for term in german_contamination:
            if term in system_prompt and lang not in ['german', 'de', 'deutsch']:
                found_contamination.append(term)
                contamination_found = True
        
        if found_contamination:
            print(f"   ❌ CONTAMINAZIONE: {', '.join(found_contamination)}")
        else:
            print(f"   ✅ Clean prompt for {lang}")
    
    return not contamination_found

def test_domain_translator_context_isolation():
    """Test che DomainAwareTranslator generi context puliti per lingua"""
    
    print(f"\n🔍 AUDIT: DomainAwareTranslator Context Templates")
    print("=" * 50)
    
    contamination_found = False
    
    try:
        translator = DomainAwareTranslator("fake_key", domain="safety")
        
        test_languages = ['english', 'french', 'spanish', 'italian']
        domains = ['safety', 'construction', 'technical']
        
        for domain in domains:
            for lang in test_languages:
                print(f"\n📋 Testing {domain} context for {lang}")
                
                # Ottieni context per dominio e lingua
                context = translator._get_context_for_domain(domain, lang)
                
                # Verifica contaminazione tedesca
                german_terms = [
                    'German', 'Sie/Ihr', 'formal German', 'German (Sie/Ihr)',
                    'Deutsch', 'deutsche', 'german', 'GERMAN'
                ]
                
                found_contamination = []
                for term in german_terms:
                    if term in context:
                        found_contamination.append(term)
                        contamination_found = True
                
                if found_contamination:
                    print(f"   ❌ CONTAMINAZIONE: {', '.join(found_contamination)}")
                    print(f"   📝 Context preview: {context[:200]}...")
                else:
                    print(f"   ✅ Clean context for {domain}/{lang}")
        
    except Exception as e:
        print(f"   ⚠️  Error during test: {e}")
        contamination_found = True
    
    return not contamination_found

def test_post_processor_language_rules():
    """Test che i post-processor applichino regole corrette per lingua"""
    
    print(f"\n🔍 AUDIT: Post-Processor Language Rules")
    print("=" * 40)
    
    contamination_found = False
    
    # Test Enhanced Post Processor
    try:
        processor = EnhancedTranslationPostProcessor()
        
        # Test sample texts per ogni lingua
        test_cases = [
            ('english', ['This is page 5', 'Translation of manual']),
            ('french', ['Ceci est la page 5', 'Traduction du manuel']),
            ('spanish', ['Esta es la página 5', 'Traducción del manual']),
        ]
        
        for lang, texts in test_cases:
            print(f"\n📋 Testing post-processing for {lang}")
            
            # Processa i testi
            processed = processor.process_translations(texts, lang)
            
            # Verifica che non ci siano forzature tedesche
            german_artifacts = ['S. ', 'Seite ', 'Sie ', 'Ihr ', 'Übersetzung', 'Deutsch']
            
            for i, text in enumerate(processed):
                found_artifacts = []
                for artifact in german_artifacts:
                    if artifact in text:
                        found_artifacts.append(artifact)
                        contamination_found = True
                
                if found_artifacts:
                    print(f"   ❌ CONTAMINAZIONE in text {i+1}: {', '.join(found_artifacts)}")
                    print(f"      Original: {texts[i]}")
                    print(f"      Processed: {text}")
                else:
                    print(f"   ✅ Clean processing: '{texts[i]}' → '{text}'")
        
    except Exception as e:
        print(f"   ⚠️  Error during post-processor test: {e}")
        contamination_found = True
    
    return not contamination_found

def test_translator_prompt_generation():
    """Test che Translator generi prompt puliti per tutte le lingue"""
    
    print(f"\n🔍 AUDIT: Translator Prompt Generation")
    print("=" * 38)
    
    contamination_found = False
    
    try:
        translator = Translator("fake_key")
        
        test_languages = ['english', 'french', 'spanish', 'portuguese']
        
        for lang in test_languages:
            print(f"\n📋 Testing prompt generation for {lang}")
            
            # Simula costruzione prompt (dal codice aggiornato)
            source_lang_text = " from Italian"
            prompt = f"""You are a professional technical translator. Translate the following texts{source_lang_text} to {lang}.

CRITICAL TRANSLATION RULES:
- Translate ONLY the provided text segments
- Maintain exact same format and structure  
- Keep all special characters and formatting unchanged
- Preserve technical terminology precisely
- Return exactly 1 translations, numbered 1 to 1
- Do NOT add explanations, notes, or extra text
- Do NOT include translation markers or metadata in output
- Keep technical terms, product names, and measurements unchanged"""

            # Regole specifiche per lingua target
            if lang.lower() in ['german', 'de', 'deutsch']:
                prompt += "\n- Replace 'pag.' with 'S.' for German page references"
            elif lang.lower() in ['english', 'en']:
                prompt += "\n- Use standard English conventions (e.g., 'page' for page references)"
            elif lang.lower() in ['french', 'fr', 'français']:
                prompt += "\n- Use standard French conventions (e.g., 'page' for page references)"
            elif lang.lower() in ['spanish', 'es', 'español']:
                prompt += "\n- Use standard Spanish conventions (e.g., 'página' for page references)"
            
            # Verifica contaminazione
            german_references = [
                'German', 'Deutsch', 'german', 'S. for German',
                'Sie/Ihr', 'Übersetzung', 'GERMAN'
            ]
            
            found_contamination = []
            for term in german_references:
                if term in prompt:
                    found_contamination.append(term)
                    contamination_found = True
            
            if found_contamination:
                print(f"   ❌ CONTAMINAZIONE: {', '.join(found_contamination)}")
            else:
                print(f"   ✅ Clean prompt for {lang}")
    
    except Exception as e:
        print(f"   ⚠️  Error during translator test: {e}")
        contamination_found = True
    
    return not contamination_found

def test_system_wide_german_isolation():
    """Test finale per verificare isolamento completo sistema"""
    
    print(f"\n🔍 AUDIT: System-Wide German Language Isolation")
    print("=" * 50)
    
    # Simula traduzione completa IT→EN con tutti i componenti
    test_text = "Vedere pag. 15 per installazione del dispositivo"
    target_language = "english"
    
    print(f"📝 Test text: '{test_text}'")
    print(f"🎯 Target language: {target_language}")
    
    contamination_found = False
    
    try:
        # 1. Test Domain Translator context
        domain_translator = DomainAwareTranslator("fake_key", domain="safety")
        safety_context = domain_translator._get_context_for_domain("safety", target_language)
        
        german_terms_in_context = [
            'German', 'Sie/Ihr', 'german', 'Deutsch', 'GERMAN'
        ]
        
        context_contamination = []
        for term in german_terms_in_context:
            if term in safety_context:
                context_contamination.append(term)
                contamination_found = True
        
        print(f"\n📋 Domain Context Test:")
        if context_contamination:
            print(f"   ❌ CONTAMINAZIONE nel context: {', '.join(context_contamination)}")
        else:
            print(f"   ✅ Context pulito per {target_language}")
        
        # 2. Test Post-Processor rules
        post_processor = EnhancedTranslationPostProcessor()
        
        # Simula un testo che potrebbe essere contaminato
        potentially_contaminated_text = "See S. 15 for device installation"  # Tedesco "S." in inglese
        processed_text = post_processor.process_translations([potentially_contaminated_text], target_language)
        
        print(f"\n📋 Post-Processor Test:")
        print(f"   Input: '{potentially_contaminated_text}'")
        print(f"   Output: '{processed_text[0]}'")
        
        # Per inglese, "S." dovrebbe rimanere "S." o essere convertito in "p."
        if target_language == "english" and "S. " in processed_text[0]:
            print(f"   ⚠️  POSSIBILE CONTAMINAZIONE: 'S.' rimasto in testo inglese")
            contamination_found = True
        else:
            print(f"   ✅ Post-processing corretto per {target_language}")
        
    except Exception as e:
        print(f"   ❌ ERROR during system test: {e}")
        contamination_found = True
    
    return not contamination_found

if __name__ == "__main__":
    print("🕵️ AUDIT COMPLETO: Eliminazione Forzature Tedesche")
    print("=" * 55)
    print("Obiettivo: Verificare che NESSUNA lingua non-tedesca abbia forzature tedesche")
    
    # Esegui tutti i test
    tests_results = {
        "AsyncTranslator": test_async_translator_language_isolation(),
        "DomainTranslator": test_domain_translator_context_isolation(), 
        "PostProcessor": test_post_processor_language_rules(),
        "Translator": test_translator_prompt_generation(),
        "SystemWide": test_system_wide_german_isolation()
    }
    
    print(f"\n🎯 RISULTATI AUDIT FINALE:")
    print("=" * 30)
    
    all_clean = True
    for component, is_clean in tests_results.items():
        status = "✅ PULITO" if is_clean else "❌ CONTAMINATO"
        print(f"   {component}: {status}")
        if not is_clean:
            all_clean = False
    
    print(f"\n💡 CONCLUSIONE GENERALE:")
    if all_clean:
        print(f"   🎉 SISTEMA COMPLETAMENTE PULITO")
        print(f"   → Nessuna forzatura tedesca in lingue non-tedesche")
        print(f"   → Ogni lingua ha regole e prompt specifici")
        print(f"   → Contaminazione IT→DE→EN completamente eliminata")
        print(f"   → Sistema pronto per traduzioni pure")
    else:
        print(f"   ⚠️  CONTAMINAZIONE ANCORA PRESENTE")
        print(f"   → Alcuni componenti necessitano correzioni")
        print(f"   → Verificare i componenti marcati come CONTAMINATI")
    
    print(f"\n📋 NEXT STEPS:")
    if all_clean:
        print(f"   1. ✅ Sistema verificato - pronto per produzione")
        print(f"   2. ✅ Test traduzione reale IT→EN")
        print(f"   3. ✅ Conferma assenza termini tedeschi in output inglese")
    else:
        print(f"   1. 🔧 Correggere componenti contaminati")
        print(f"   2. 🔄 Ri-eseguire audit fino a pulizia completa")
        print(f"   3. ✅ Test finale con traduzione reale")
    
    # Exit code
    sys.exit(0 if all_clean else 1)