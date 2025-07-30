#!/usr/bin/env python3
"""
Test per verificare parole mancanti: ASSEMBLAGGIO, MONTAGGIO, COMPONENTI
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from text_extractor import TextExtractor

def test_missing_words():
    """Test delle parole segnalate come mancanti"""
    
    print("🔍 Test Parole Mancanti Segnalate")
    print("=" * 40)
    
    # Parole segnalate come problematiche
    missing_words = [
        'ASSEMBLAGGIO',  # Assembly/Assemblage/Montaje
        'MONTAGGIO',     # Mounting/Montage/Montaje  
        'COMPONENTI',    # Components/Composants/Componentes
    ]
    
    # Test varianti ortografiche
    word_variants = {
        'ASSEMBLAGGIO': ['ASSEMBLAGGIO', 'ASSEM BLAGGIO', 'ASSEMBLRAGGIO'],  # Include errore di battitura
        'MONTAGGIO': ['MONTAGGIO', 'MONTAGGI'],
        'COMPONENTI': ['COMPONENTI', 'COMPONENTE'],
    }
    
    languages = ['de', 'en', 'fr', 'es']
    
    print(f"🎯 Testando parole problematiche in {len(languages)} lingue")
    
    results = {}
    
    for lang in languages:
        print(f"\n📚 Lingua: {lang.upper()}")
        extractor = TextExtractor()
        
        for word in missing_words:
            is_translatable = extractor._is_translatable_text(word, lang)
            status = "✅" if is_translatable else "❌ MANCANTE"
            action = "TRADUCE" if is_translatable else "IGNORA"
            
            print(f"   {word:15} {status} {action}")
            
            # Test varianti se la parola principale fallisce
            if not is_translatable and word in word_variants:
                print(f"   → Test varianti per {word}:")
                for variant in word_variants[word]:
                    var_translatable = extractor._is_translatable_text(variant, lang)
                    var_status = "✅" if var_translatable else "❌"
                    print(f"     {variant:15} {var_status}")
    
    return True

def show_current_dictionary_coverage():
    """Mostra copertura attuale dei dizionari"""
    
    print(f"\n📚 Verifica Copertura Dizionari Attuali")
    print("=" * 45)
    
    # Simulazione: leggi le parole attualmente nei dizionari
    extractor = TextExtractor()
    
    test_words = [
        'ASSEMBLAGGIO', 'MONTAGGIO', 'COMPONENTI', 'COMPONENTE',
        'INSTALLAZIONE', 'FISSAGGIO', 'SICUREZZA', 'SISTEMA'
    ]
    
    for lang in ['de', 'en', 'fr', 'es']:
        print(f"\n{lang.upper()}:")
        found_words = []
        missing_words = []
        
        for word in test_words:
            is_found = extractor._is_translatable_text(word, lang)
            if is_found:
                found_words.append(word)
            else:
                missing_words.append(word)
        
        print(f"   ✅ Trovate ({len(found_words)}): {', '.join(found_words) if found_words else 'Nessuna'}")
        print(f"   ❌ Mancanti ({len(missing_words)}): {', '.join(missing_words) if missing_words else 'Nessuna'}")

if __name__ == "__main__":
    print("🔧 Test Parole Mancanti: ASSEMBLAGGIO, MONTAGGIO, COMPONENTI")
    print("=" * 65)
    
    # Test parole mancanti
    test_missing_words()
    
    # Mostra copertura attuale
    show_current_dictionary_coverage()
    
    print(f"\n💡 RISULTATO:")
    print(f"   Le parole mancanti devono essere aggiunte ai dizionari")
    print(f"   Procedo con l'aggiornamento dei dizionari...")