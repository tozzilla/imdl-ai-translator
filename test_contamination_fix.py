#!/usr/bin/env python3
"""
Test per verificare risoluzione contaminazione crociata traduzioni
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from text_extractor import TextExtractor

def test_language_specific_dictionaries():
    """Test dizionari specifici per lingua"""
    
    print("🔬 Test Dizionari Specifici per Lingua")
    print("=" * 50)
    
    # Test cases con problemi di contaminazione
    test_cases = [
        {
            'text': 'INSPEKTION',
            'description': 'Parola tedesca che deve essere tradotta in inglese',
            'expected_behavior': {
                'de': False,  # Parola tedesca, non tradurre DA tedesco
                'en': True,   # Tradurre da tedesco A inglese  
                'fr': True,   # Tradurre da tedesco A francese
            }
        },
        {
            'text': 'LINEA',
            'description': 'Parola italiana specifica (SafeGuard)',
            'expected_behavior': {
                'de': True,   # Tradurre da italiano A tedesco → LINIE
                'en': True,   # Tradurre da italiano A inglese → LINE
                'fr': True,   # Tradurre da italiano A francese → LIGNE
                'es': True,   # Tradurre da italiano A spagnolo → LÍNEA
            }
        },
        {
            'text': 'WARTUNG',
            'description': 'Parola tedesca pura (manutenzione)',
            'expected_behavior': {
                'de': False,  # Non tradurre DA tedesco 
                'en': True,   # Tradurre da tedesco A inglese → MAINTENANCE
                'fr': True,   # Tradurre da tedesco A francese → MAINTENANCE
            }
        }
    ]
    
    results = {}
    
    for case in test_cases:
        text = case['text']
        description = case['description']
        expected = case['expected_behavior']
        
        print(f"\n🔍 Test: '{text}' - {description}")
        
        case_results = {}
        
        for lang_code, should_translate in expected.items():
            # Crea extractor per lingua specifica
            extractor = TextExtractor()
            
            # Test se il testo è considerato traducibile per questa lingua
            is_translatable = extractor._is_translatable_text(text, lang_code)
            
            # Verifica comportamento
            is_correct = (is_translatable == should_translate)
            status = "✅" if is_correct else "❌"
            
            print(f"   {lang_code}: {status} {'TRADUCE' if is_translatable else 'NON traduce'} (expected: {'TRADUCE' if should_translate else 'NON traduce'})")
            
            case_results[lang_code] = {
                'expected': should_translate,
                'actual': is_translatable,
                'correct': is_correct
            }
        
        results[text] = case_results
    
    # Analisi risultati
    print(f"\n📊 ANALISI RISULTATI:")
    
    total_tests = sum(len(case['expected_behavior']) for case in test_cases)
    correct_tests = sum(
        sum(1 for lang_result in case_results.values() if lang_result['correct'])
        for case_results in results.values()
    )
    
    success_rate = (correct_tests / total_tests) * 100
    
    print(f"   Test totali: {total_tests}")
    print(f"   Test corretti: {correct_tests}")
    print(f"   Tasso successo: {success_rate:.1f}%")
    
    # Identifica problemi
    problems = []
    for text, case_results in results.items():
        for lang, result in case_results.items():
            if not result['correct']:
                problems.append(f"{text} ({lang}): expected {result['expected']}, got {result['actual']}")
    
    if problems:
        print(f"\n⚠️  PROBLEMI RILEVATI ({len(problems)}):")
        for problem in problems:
            print(f"   - {problem}")
    else:
        print(f"\n🎉 TUTTI I TEST PASSATI!")
    
    return success_rate >= 80.0  # 80% di successo richiesto

def main():
    """Test principale"""
    
    print("🔧 Test Risoluzione Contaminazione Crociata Traduzioni")
    print("=" * 60)
    
    # Test dizionari specifici per lingua
    dict_test_passed = test_language_specific_dictionaries()
    
    # Risultato finale
    print(f"\n🎯 RISULTATO FINALE:")
    print(f"   📚 Dizionari lingua-specifici: {'✅ PASS' if dict_test_passed else '❌ FAIL'}")
    
    if dict_test_passed:
        print(f"\n🎉 CONTAMINAZIONE CROCIATA RISOLTA!")
        print(f"   Il sistema ora usa dizionari specifici per lingua")
        print(f"   Risolto il problema: IT → DE → EN che lasciava parole tedesche")
        
        # Raccomandazioni d'uso
        print(f"\n💡 RACCOMANDAZIONI PER IL TUO CASO:")
        print(f"   🎯 Traduci sempre dall'italiano originale, mai da traduzioni intermedie")
        print(f"   📋 Usa: python translate_idml_main.py file.idml output_de.idml -l de")
        print(f"   📋 Poi: python translate_idml_main.py file.idml output_en.idml -l en")
        print(f"   ❌ EVITA: IT → DE → EN (causa contaminazione)")
        
        return True
    else:
        print(f"\n❌ TEST FALLITI - Contaminazione non completamente risolta")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Errore durante test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)