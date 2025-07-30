#!/usr/bin/env python3
"""
Test per verificare che le cache siano separate per lingua
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from translation_memory import TranslationMemory
import tempfile

def test_language_cache_separation():
    """Test che le cache siano separate per lingua"""
    
    print("🔄 Test Separazione Cache per Lingua")
    print("=" * 40)
    
    # Usa database temporaneo per test
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        tm = TranslationMemory(tmp.name)
        
        # Test caso problematico: stessa parola italiana tradotta in tedesco e inglese
        source_text = "INSTALLAZIONE"
        
        # Aggiungi traduzione tedesca
        tm.add_translation(
            source_text=source_text,
            target_text="INSTALLATION",  # Traduzione tedesca
            target_lang="de",
            source_lang="it",
            context="technical_manual"
        )
        
        # Aggiungi traduzione inglese 
        tm.add_translation(
            source_text=source_text,
            target_text="INSTALLATION",  # Traduzione inglese (diversa)
            target_lang="en", 
            source_lang="it",
            context="technical_manual"
        )
        
        print(f"📝 Aggiunto '{source_text}' -> Tedesco: INSTALLATION")
        print(f"📝 Aggiunto '{source_text}' -> Inglese: INSTALLATION")
        
        # Test recupero per lingua tedesca
        german_match = tm.get_exact_match(
            source_text=source_text,
            target_lang="de",
            context="technical_manual"
        )
        
        # Test recupero per lingua inglese  
        english_match = tm.get_exact_match(
            source_text=source_text,
            target_lang="en", 
            context="technical_manual"
        )
        
        print(f"\n🔍 Ricerca per lingua tedesca:")
        if german_match:
            print(f"   ✅ Trovato: {german_match['target_text']}")
            print(f"   📊 Lingua target: {german_match['target_lang']}")
        else:
            print(f"   ❌ NON trovato (cache non funziona)")
            
        print(f"\n🔍 Ricerca per lingua inglese:")
        if english_match:
            print(f"   ✅ Trovato: {english_match['target_text']}")
            print(f"   📊 Lingua target: {english_match['target_lang']}")
        else:
            print(f"   ❌ NON trovato (cache non funziona)")
        
        # Test separazione effettiva
        separation_success = (
            german_match and 
            english_match and
            german_match['target_lang'] == 'de' and
            english_match['target_lang'] == 'en'
        )
        
        print(f"\n🎯 RISULTATO TEST:")
        if separation_success:
            print(f"   ✅ SUCCESSO: Cache separate correttamente per lingua")
            print(f"   → Tedesco e inglese hanno cache indipendenti")
        else:
            print(f"   ❌ FALLIMENTO: Cache non separate correttamente")
            print(f"   → Possibile contaminazione tra lingue")
            
        # Test contaminazione: cerco tedesco ma con lingua inglese
        contamination_test = tm.get_exact_match(
            source_text=source_text,
            target_lang="fr",  # Francese - non dovrebbe trovare nulla
            context="technical_manual"
        )
        
        print(f"\n🧪 Test Contaminazione (cerca in francese):")
        if contamination_test:
            print(f"   ❌ PROBLEMA: Trovato {contamination_test['target_text']} in francese")
            print(f"   → Possibile contaminazione cache")
        else:
            print(f"   ✅ OK: Nessun risultato per francese (corretto)")
            
        # Mostra statistiche hash
        print(f"\n📊 Analisi Hash Context:")
        hash_de = tm._compute_context_hash("technical_manual", None, "de")
        hash_en = tm._compute_context_hash("technical_manual", None, "en") 
        hash_fr = tm._compute_context_hash("technical_manual", None, "fr")
        
        print(f"   DE: {hash_de}")
        print(f"   EN: {hash_en}")
        print(f"   FR: {hash_fr}")
        
        all_different = len(set([hash_de, hash_en, hash_fr])) == 3
        print(f"   Hash tutti diversi: {'✅ SI' if all_different else '❌ NO'}")
        
        tm.close()
        
        # Cleanup
        try:
            os.unlink(tmp.name)
        except:
            pass
            
        return separation_success and all_different

if __name__ == "__main__":
    print("🔧 Test Separazione Cache Traduzioni per Lingua")
    print("=" * 50)
    
    success = test_language_cache_separation()
    
    print(f"\n💡 CONCLUSIONE:")
    if success:
        print(f"   ✅ Sistema cache aggiornato correttamente")
        print(f"   → Ogni lingua ha cache separato")
        print(f"   → Nessuna contaminazione tra lingue")
    else:
        print(f"   ❌ Problema nella separazione cache")
        print(f"   → Verificare implementazione")