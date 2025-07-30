#!/usr/bin/env python3
"""
Script per pulire cache contaminato dalle traduzioni precedenti
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from translation_memory import TranslationMemory
from pathlib import Path

def clear_contaminated_cache():
    """Pulisce la cache contaminato dalle traduzioni incrociate"""
    
    print("🧹 Pulizia Cache Contaminato")
    print("=" * 30)
    
    # Trova il database TM default
    default_dir = Path.home() / '.translate-idml'
    db_path = default_dir / 'tm.db'
    
    if not db_path.exists():
        print("ℹ️  Nessun database cache esistente trovato")
        print("   La pulizia non è necessaria")
        return True
        
    print(f"📁 Database trovato: {db_path}")
    
    # Apri connessione
    tm = TranslationMemory(str(db_path))
    
    # Mostra statistiche pre-pulizia
    stats_before = tm.get_statistics()
    print(f"📊 Statistiche PRE-pulizia:")
    print(f"   → Traduzioni totali: {stats_before['total_translations']}")
    print(f"   → Lingue principali: {', '.join([f'{lang}({count})' for lang, count in stats_before['top_languages']])}")
    
    # Identifica traduzioni potenzialmente contaminate
    # Cerca coppie sospette: stessa source_text con target_lang diversi ma risultati simili
    cursor = tm.conn.execute("""
        SELECT source_text, target_text, target_lang, COUNT(*) as lang_count
        FROM translations 
        WHERE source_text IN (
            SELECT source_text 
            FROM translations 
            GROUP BY source_text 
            HAVING COUNT(DISTINCT target_lang) > 1
        )
        GROUP BY source_text, target_text
        HAVING lang_count > 1
        ORDER BY source_text
    """)
    
    suspicious_translations = cursor.fetchall()
    
    print(f"\n🔍 Analisi Contaminazione:")
    print(f"   → Traduzioni sospette trovate: {len(suspicious_translations)}")
    
    if suspicious_translations:
        print(f"   → Esempi di possibile contaminazione:")
        for row in suspicious_translations[:5]:  # Mostra solo primi 5
            print(f"     '{row['source_text']}' -> '{row['target_text']}' ({row['lang_count']} lingue)")
    
    # Opzione 1: Pulizia completa (raccomandato per risolvere contaminazione)
    print(f"\n🗑️  Pulizia Completa Cache:")
    print(f"   → Rimuove TUTTE le traduzioni esistenti")
    print(f"   → Garantisce nessuna contaminazione futura")
    print(f"   → Le nuove traduzioni useranno cache separato per lingua")
    
    # Esegui pulizia completa
    tm.conn.execute("DELETE FROM translations")
    tm.conn.commit()
    
    # Verifica pulizia
    stats_after = tm.get_statistics()
    print(f"\n📊 Statistiche POST-pulizia:")
    print(f"   → Traduzioni totali: {stats_after['total_translations']}")
    
    # Mantieni terminologia e regole (non sono contaminate)
    print(f"   → Terminologia conservata: {stats_after['total_terms']} termini")
    print(f"   → Regole conservate: {stats_after['active_rules']} regole")
    
    tm.close()
    
    print(f"\n✅ PULIZIA COMPLETA:")
    print(f"   → Cache completamente pulito")
    print(f"   → Sistema pronto per traduzioni senza contaminazione")
    print(f"   → Ogni lingua avrà cache separato e indipendente")
    
    return True

def backup_terminology():
    """Crea backup della terminologia prima della pulizia"""
    
    print("💾 Backup Terminologia")
    print("=" * 20)
    
    default_dir = Path.home() / '.translate-idml'
    db_path = default_dir / 'tm.db'
    
    if not db_path.exists():
        print("ℹ️  Nessuna terminologia da salvare")
        return
        
    tm = TranslationMemory(str(db_path))
    stats = tm.get_statistics()
    
    if stats['total_terms'] > 0:
        backup_path = default_dir / 'terminology_backup.json'
        
        # Esporta terminologia
        cursor = tm.conn.execute("SELECT * FROM terminology")
        terms = [dict(row) for row in cursor]
        
        import json
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(terms, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"📁 Terminologia salvata in: {backup_path}")
        print(f"   → {len(terms)} termini salvati")
    else:
        print("ℹ️  Nessuna terminologia da salvare")
        
    tm.close()

if __name__ == "__main__":
    print("🧹 Pulizia Cache Contaminato - Traduzioni Multi-lingua")
    print("=" * 55)
    
    # Backup prima della pulizia
    backup_terminology()
    
    print()
    
    # Pulizia cache
    success = clear_contaminated_cache()
    
    print(f"\n💡 RISULTATO:")
    if success:
        print(f"   ✅ Cache pulito con successo")
        print(f"   ✅ Sistema pronto per traduzioni pure") 
        print(f"   → Ogni lingua avrà cache indipendente")
        print(f"   → Nessuna contaminazione futura tra lingue")
    else:
        print(f"   ❌ Problema durante la pulizia")
    
    print(f"\n📋 PROSSIMI PASSI:")
    print(f"   1. ✅ Cache separato per lingua implementato")
    print(f"   2. ✅ Cache esistente pulito") 
    print(f"   3. → Pronto per traduzioni senza contaminazione")