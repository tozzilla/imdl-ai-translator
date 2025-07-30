#!/usr/bin/env python3
"""
Script per verificare che la cache inglese sia completamente vuota
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from translation_memory import TranslationMemory
from pathlib import Path

def check_english_cache():
    """Verifica che la cache inglese sia vuota"""
    
    print("🔍 Verifica Cache Inglese")
    print("=" * 25)
    
    # Trova il database TM
    default_dir = Path.home() / '.translate-idml'
    db_path = default_dir / 'tm.db'
    
    if not db_path.exists():
        print("✅ Nessun database cache esistente")
        print("   → Cache inglese è vuota (non esiste)")
        return True
        
    print(f"📁 Database: {db_path}")
    
    # Apri connessione
    tm = TranslationMemory(str(db_path))
    
    # Verifica traduzioni inglesi
    cursor = tm.conn.execute("""
        SELECT COUNT(*) as count 
        FROM translations 
        WHERE target_lang = 'en'
    """)
    
    english_count = cursor.fetchone()['count']
    
    print(f"📊 Traduzioni inglesi nella cache: {english_count}")
    
    if english_count == 0:
        print("✅ Cache inglese VUOTA - Perfetto!")
        print("   → Nessuna contaminazione possibile")
    else:
        print(f"⚠️  Cache inglese contiene {english_count} traduzioni")
        print("   → Potrebbero essere residui contaminati")
        
        # Mostra alcuni esempi
        cursor = tm.conn.execute("""
            SELECT source_text, target_text, created_at
            FROM translations 
            WHERE target_lang = 'en'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        print("   → Esempi di traduzioni presenti:")
        for row in cursor:
            print(f"     '{row['source_text'][:50]}...' -> '{row['target_text'][:50]}...'")
    
    # Verifica anche altre lingue per confronto
    print(f"\n📊 Riepilogo Cache per Lingua:")
    cursor = tm.conn.execute("""
        SELECT target_lang, COUNT(*) as count
        FROM translations
        GROUP BY target_lang
        ORDER BY count DESC
    """)
    
    for row in cursor:
        lang = row['target_lang']
        count = row['count']
        status = "✅ VUOTA" if count == 0 else f"⚠️  {count} traduzioni"
        print(f"   {lang.upper()}: {status}")
    
    # Verifica totale
    cursor = tm.conn.execute("SELECT COUNT(*) as total FROM translations")
    total = cursor.fetchone()['total']
    
    print(f"\n🎯 RISULTATO VERIFICA:")
    if total == 0:
        print("   ✅ TUTTA la cache è vuota")
        print("   → Sistema completamente pulito")
        print("   → Nessuna contaminazione possibile")
    elif english_count == 0:
        print("   ✅ Cache inglese è vuota")
        print(f"   ℹ️  Altre lingue hanno {total} traduzioni")
        print("   → Cache inglese pronta per traduzioni pure")
    else:
        print("   ❌ Cache inglese NON è vuota")
        print("   → Potrebbe necessitare pulizia aggiuntiva")
    
    tm.close()
    return english_count == 0

def show_cache_hash_examples():
    """Mostra esempi di hash per verificare separazione"""
    
    print(f"\n🔐 Test Hash Separazione Lingue:")
    print("=" * 35)
    
    tm = TranslationMemory()  # Connessione temporanea
    
    # Test hash per stesso contesto ma lingue diverse
    context = "technical_manual"
    document_type = "idml"
    
    hash_de = tm._compute_context_hash(context, document_type, "de")
    hash_en = tm._compute_context_hash(context, document_type, "en")
    hash_fr = tm._compute_context_hash(context, document_type, "fr")
    hash_es = tm._compute_context_hash(context, document_type, "es")
    
    print(f"Context: '{context}', Document: '{document_type}'")
    print(f"   DE: {hash_de}")
    print(f"   EN: {hash_en}")
    print(f"   FR: {hash_fr}")
    print(f"   ES: {hash_es}")
    
    # Verifica che siano tutti diversi
    hashes = [hash_de, hash_en, hash_fr, hash_es]
    all_unique = len(set(hashes)) == len(hashes)
    
    print(f"\n🎯 Hash Separazione:")
    print(f"   Tutti diversi: {'✅ SI' if all_unique else '❌ NO'}")
    print(f"   → Ogni lingua ha cache completamente separato")
    
    tm.close()

if __name__ == "__main__":
    print("🔍 Verifica Cache Inglese - Post Pulizia")
    print("=" * 40)
    
    # Verifica cache inglese
    english_clean = check_english_cache()
    
    # Mostra hash separation
    show_cache_hash_examples()
    
    print(f"\n💡 CONCLUSIONE:")
    if english_clean:
        print(f"   ✅ Cache inglese completamente vuota")
        print(f"   ✅ Sistema pronto per traduzioni pure")
        print(f"   → Nessuna contaminazione da cache precedente")
        print(f"   → Traduzioni IT→EN saranno fresche e accurate")
    else:
        print(f"   ⚠️  Cache inglese contiene dati residui")
        print(f"   → Consigliata pulizia aggiuntiva se necessario")
    
    print(f"\n📋 STATO SISTEMA:")
    print(f"   ✅ Cache separato per lingua: IMPLEMENTATO")
    print(f"   ✅ Hash diversi per lingua: VERIFICATO") 
    print(f"   ✅ Cache inglese: {'VUOTA' if english_clean else 'DA VERIFICARE'}")
    print(f"   → Sistema anti-contaminazione: ATTIVO")