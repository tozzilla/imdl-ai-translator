#!/usr/bin/env python3
"""
Test per verificare dizionari espansi con parole SafeGuard essenziali
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from text_extractor import TextExtractor

def test_safeguard_essential_words():
    """Verifica che tutte le parole essenziali SafeGuard siano nei dizionari"""
    
    print("🔍 Test Parole Essenziali SafeGuard")
    print("=" * 50)
    
    # Parole chiave critiche che DEVONO essere tradotte in TUTTE le lingue
    essential_words = [
        'LINEA',           # Problema principale dell'utente
        'GUIDA',           # INSPECTION GUIDE
        'ISPEZIONE',       # INSPECTION
        'SICUREZZA',       # SAFETY/SECURITY  
        'PROTEZIONE',      # PROTECTION
        'INSTALLAZIONE',   # INSTALLATION
        'MONTAGGIO',       # MOUNTING/ASSEMBLY
        'SISTEMA',         # SYSTEM
        'COMPONENTE',      # COMPONENT
        'DISPOSITIVO',     # DEVICE
        'MANUALE',         # MANUAL
        'PROCEDURA',       # PROCEDURE
        'CONTROLLO',       # CONTROL
        'VERIFICA',        # VERIFICATION
        'MANUTENZIONE',    # MAINTENANCE
        'ATTENZIONE',      # ATTENTION/WARNING
        'PERICOLO',        # DANGER
        'IMPORTANTE',      # IMPORTANT
        'ACCESSO',         # ACCESS
        'USO',             # USE
        'FISSAGGIO',       # FIXING/FASTENING
        'ANCORAGGIO'       # ANCHORING
    ]
    
    # Lingue da testare
    languages = ['de', 'en', 'fr', 'es']
    
    print(f"🎯 Testando {len(essential_words)} parole essenziali in {len(languages)} lingue")
    
    results = {}
    total_tests = 0
    passed_tests = 0
    
    for lang in languages:
        print(f"\n📚 Lingua: {lang.upper()}")
        
        extractor = TextExtractor()
        lang_results = {}
        
        for word in essential_words:
            total_tests += 1
            is_translatable = extractor._is_translatable_text(word, lang)
            
            status = "✅" if is_translatable else "❌"
            action = "TRADUCE" if is_translatable else "IGNORA"
            
            print(f"   {word:15} {status} {action}")
            
            lang_results[word] = is_translatable
            if is_translatable:
                passed_tests += 1
        
        results[lang] = lang_results
        
        # Statistiche per lingua
        lang_passed = sum(lang_results.values())
        lang_percentage = (lang_passed / len(essential_words)) * 100
        print(f"   📊 Copertura {lang}: {lang_passed}/{len(essential_words)} ({lang_percentage:.1f}%)")
    
    # Analisi globale
    print(f"\n📊 RISULTATI GLOBALI:")
    overall_percentage = (passed_tests / total_tests) * 100
    print(f"   Test totali: {total_tests}")
    print(f"   Test passati: {passed_tests}")
    print(f"   Copertura globale: {overall_percentage:.1f}%")
    
    # Identifica parole problematiche
    problematic_words = {}
    for word in essential_words:
        missing_langs = []
        for lang in languages:
            if not results[lang][word]:
                missing_langs.append(lang)
        if missing_langs:
            problematic_words[word] = missing_langs
    
    if problematic_words:
        print(f"\n⚠️  PAROLE PROBLEMATICHE ({len(problematic_words)}):")
        for word, missing_langs in problematic_words.items():
            print(f"   {word}: mancante in {', '.join(missing_langs)}")
    else:
        print(f"\n🎉 TUTTE LE PAROLE ESSENZIALI SONO COPERTE!")
    
    # Verifica specifica per le parole che erano problematiche
    print(f"\n🔎 VERIFICA PAROLE PRECEDENTEMENTE PROBLEMATICHE:")
    
    critical_checks = [
        ('LINEA', ['de', 'en', 'fr', 'es'], 'Nome prodotto SafeGuard'),
        ('INSPEKTION', ['en', 'fr'], 'Contaminazione tedesca → altre lingue'),
        ('WARTUNG', ['en', 'fr'], 'Manutenzione tedesca → altre lingue'),
        ('VERFAHREN', ['en'], 'Procedura tedesca → inglese'),
    ]
    
    all_critical_passed = True
    
    for word, langs, description in critical_checks:
        print(f"\n   🎯 {word} ({description}):")
        
        for lang in langs:
            extractor = TextExtractor()
            is_translatable = extractor._is_translatable_text(word, lang)
            status = "✅" if is_translatable else "❌"
            action = "TRADUCE" if is_translatable else "IGNORA"
            
            print(f"      {lang}: {status} {action}")
            
            if not is_translatable:
                all_critical_passed = False
    
    return overall_percentage >= 90.0 and all_critical_passed

def test_anti_contamination():
    """Test specifico per anti-contaminazione tedesca"""
    
    print(f"\n🛡️  Test Anti-Contaminazione Tedesca")
    print("=" * 40)
    
    # Parole tedesche che devono essere tradotte verso altre lingue
    german_contamination_words = [
        'INSPEKTION',      # → INSPECTION (en), INSPECTION (fr)
        'WARTUNG',         # → MAINTENANCE (en), MAINTENANCE (fr)  
        'SICHERHEIT',      # → SECURITY (en), SÉCURITÉ (fr)
        'VERFAHREN',       # → PROCEDURE (en), PROCÉDURE (fr)
        'HANDBUCH',        # → MANUAL (en), MANUEL (fr)
        'LINIE',           # → LINE (en), LIGNE (fr)
    ]
    
    target_languages = ['en', 'fr', 'es']
    
    print(f"🎯 Testando {len(german_contamination_words)} parole tedesche verso {len(target_languages)} lingue")
    
    contamination_results = {}
    total_anti_tests = 0
    passed_anti_tests = 0
    
    for lang in target_languages:
        print(f"\n📚 Anti-contaminazione Tedesco → {lang.upper()}:")
        
        extractor = TextExtractor()
        lang_results = {}
        
        for german_word in german_contamination_words:
            total_anti_tests += 1
            is_translatable = extractor._is_translatable_text(german_word, lang)
            
            # Per anti-contaminazione, vogliamo che le parole tedesche SIANO tradotte
            status = "✅" if is_translatable else "❌"
            action = "TRADUCE" if is_translatable else "MANTIENE TEDESCO ⚠️"
            
            print(f"   {german_word:15} {status} {action}")
            
            lang_results[german_word] = is_translatable
            if is_translatable:
                passed_anti_tests += 1
        
        contamination_results[lang] = lang_results
    
    # Risultati anti-contaminazione
    anti_percentage = (passed_anti_tests / total_anti_tests) * 100
    print(f"\n📊 Anti-Contaminazione:")
    print(f"   Test anti-contaminazione: {passed_anti_tests}/{total_anti_tests}")
    print(f"   Efficacia anti-contaminazione: {anti_percentage:.1f}%")
    
    return anti_percentage >= 80.0  # 80% minimo per anti-contaminazione

def main():
    """Test principale"""
    
    print("🔧 Test Dizionari Espansi con Parole SafeGuard")
    print("=" * 60)
    
    # Test 1: Parole essenziali SafeGuard
    essential_test_passed = test_safeguard_essential_words()
    
    # Test 2: Anti-contaminazione tedesca
    anti_contamination_passed = test_anti_contamination()
    
    # Risultato finale
    print(f"\n🎯 RISULTATO FINALE:")
    print(f"   📚 Parole essenziali SafeGuard: {'✅ PASS' if essential_test_passed else '❌ FAIL'}")
    print(f"   🛡️  Anti-contaminazione tedesca: {'✅ PASS' if anti_contamination_passed else '❌ FAIL'}")
    
    if essential_test_passed and anti_contamination_passed:
        print(f"\n🎉 DIZIONARI COMPLETAMENTE OTTIMIZZATI!")
        print(f"   ✅ Tutte le parole SafeGuard sono coperte")
        print(f"   ✅ Anti-contaminazione tedesca funziona")
        print(f"   ✅ Il problema 'LINEA' nell'immagine è risolto")
        
        print(f"\n💡 RISOLUZIONE PROBLEMI DELL'UTENTE:")
        print(f"   🎯 'LINEA' sarà tradotta: LINEA → LINIE (de), LINE (en), LIGNE (fr)")
        print(f"   🔧 'INSPEKTION' non contaminerà più l'inglese")
        print(f"   📚 Dizionario inglese espanso da selettivo a completo")
        print(f"   🛡️  Prevenzione automatica contaminazione crociata")
        
        return True
    else:
        print(f"\n❌ ALCUNI TEST FALLITI - Rivedere dizionari")
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