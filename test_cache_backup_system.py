#!/usr/bin/env python3
"""
Test per il sistema di backup cache
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from cache_backup_manager import CacheBackupManager
from translation_memory import TranslationMemory
import tempfile
import shutil
from pathlib import Path

def test_cache_backup_system():
    """Test completo del sistema backup cache"""
    
    print("🧪 Test Sistema Backup Cache")
    print("=" * 30)
    
    # Usa directory temporanea per test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Simula database cache con dati
        test_db = temp_path / "tm.db"
        tm = TranslationMemory(str(test_db))
        
        # Aggiungi dati test
        test_translations = [
            ("INSTALLAZIONE", "INSTALLATION", "de", "it", "technical_manual"),
            ("ASSEMBLAGGIO", "MONTAGE", "de", "it", "technical_manual"),
            ("COMPONENTI", "KOMPONENTEN", "de", "it", "technical_manual"),
            ("INSTALLAZIONE", "INSTALLATION", "en", "it", "technical_manual"),
            ("ASSEMBLAGGIO", "ASSEMBLY", "en", "it", "technical_manual"),
        ]
        
        for source, target, target_lang, source_lang, context in test_translations:
            tm.add_translation(source, target, target_lang, source_lang, context)
        
        initial_stats = tm.get_statistics()
        tm.close()
        
        print(f"📊 Dati Test Creati:")
        print(f"   → {initial_stats['total_translations']} traduzioni")
        print(f"   → Lingue: {', '.join([lang for lang, _ in initial_stats['top_languages']])}")
        
        # Test 1: Creazione backup
        print(f"\n🔧 Test 1: Creazione Backup")
        
        # Crea manager per test con path temporanei
        manager = CacheBackupManager()
        manager.default_dir = temp_path
        manager.db_path = test_db
        manager.backup_dir = temp_path / "backups"
        manager.backup_dir.mkdir(exist_ok=True)
        
        backup_path = manager.create_backup("test_backup")
        
        if backup_path and Path(backup_path).exists():
            print("   ✅ Backup creato correttamente")
        else:
            print("   ❌ Backup NON creato")
            return False
        
        # Test 2: Lista backup
        print(f"\n🔧 Test 2: Lista Backup")
        backups = manager.list_backups()
        
        if len(backups) == 1 and backups[0]['name'] == 'test_backup':
            print("   ✅ Lista backup funziona")
            print(f"   → Backup: {backups[0]['name']}")
            print(f"   → Traduzioni: {backups[0].get('total_translations', 'N/A')}")
        else:
            print(f"   ❌ Lista backup errata: {len(backups)} backup trovati")
            return False
        
        # Test 3: Modifica cache attuale
        print(f"\n🔧 Test 3: Modifica Cache e Differenze")
        
        # Aggiungi nuove traduzioni alla cache attuale
        tm = TranslationMemory(str(test_db))
        tm.add_translation("CONTROLLO", "KONTROLLE", "de", "it", "technical_manual")
        tm.add_translation("CONTROLLO", "CONTROL", "en", "it", "technical_manual")
        new_stats = tm.get_statistics()
        tm.close()
        
        print(f"   → Traduzioni attuali: {new_stats['total_translations']}")
        
        # Test differenze
        diff = manager.analyze_backup_differences("test_backup")
        
        if 'error' in diff:
            print(f"   ❌ Errore analisi differenze: {diff['error']}")
            return False
        
        expected_diff = new_stats['total_translations'] - initial_stats['total_translations']
        
        if diff['translation_diff'] == expected_diff:
            print(f"   ✅ Analisi differenze corretta: +{diff['translation_diff']} traduzioni")
        else:
            print(f"   ❌ Analisi differenze errata: {diff['translation_diff']} vs {expected_diff}")
            return False
        
        # Test 4: Ripristino backup
        print(f"\n🔧 Test 4: Ripristino Backup")
        
        # Ripristina backup (con conferma automatica)
        success = manager.restore_backup("test_backup", confirm=True)
        
        if success:
            # Verifica ripristino
            tm = TranslationMemory(str(test_db))
            restored_stats = tm.get_statistics()
            tm.close()
            
            if restored_stats['total_translations'] == initial_stats['total_translations']:
                print("   ✅ Ripristino backup riuscito")
                print(f"   → Traduzioni ripristinate: {restored_stats['total_translations']}")
            else:
                print(f"   ❌ Ripristino errato: {restored_stats['total_translations']} vs {initial_stats['total_translations']}")
                return False
        else:
            print("   ❌ Ripristino backup fallito")
            return False
        
        # Test 5: Eliminazione backup
        print(f"\n🔧 Test 5: Eliminazione Backup")
        
        delete_success = manager.delete_backup("test_backup", confirm=True)
        
        if delete_success:
            # Verifica eliminazione
            remaining_backups = manager.list_backups()
            if len(remaining_backups) == 0:
                print("   ✅ Eliminazione backup riuscita")
            else:
                print(f"   ❌ Backup non eliminato: {len(remaining_backups)} rimasti")
                return False
        else:
            print("   ❌ Eliminazione backup fallita")
            return False
        
        # Test completato con ambiente isolato
        
        print(f"\n🎯 TUTTI I TEST SUPERATI:")
        print(f"   ✅ Creazione backup")
        print(f"   ✅ Lista backup")
        print(f"   ✅ Analisi differenze")
        print(f"   ✅ Ripristino backup")
        print(f"   ✅ Eliminazione backup")
        
        return True

def test_cache_integration():
    """Test integrazione con sistema cache esistente"""
    
    print(f"\n🔗 Test Integrazione Cache Reale")
    print("=" * 35)
    
    manager = CacheBackupManager()
    
    # Verifica directory backup
    if manager.backup_dir.exists():
        print(f"✅ Directory backup: {manager.backup_dir}")
    else:
        print(f"⚠️  Directory backup creata: {manager.backup_dir}")
        manager.backup_dir.mkdir(exist_ok=True)
    
    # Lista backup esistenti
    existing_backups = manager.list_backups()
    print(f"📋 Backup esistenti: {len(existing_backups)}")
    
    for backup in existing_backups[:3]:  # Mostra primi 3
        name = backup['name']
        created = backup['created'].strftime("%Y-%m-%d %H:%M")
        translations = backup.get('total_translations', 'N/A')
        print(f"   → {name} ({created}) - {translations} traduzioni")
    
    # Verifica cache attuale
    if manager.db_path.exists():
        tm = TranslationMemory()
        current_stats = tm.get_statistics()
        tm.close()
        
        print(f"\n📊 Cache Attuale:")
        print(f"   → Traduzioni: {current_stats['total_translations']}")
        print(f"   → Lingue: {', '.join([lang for lang, _ in current_stats['top_languages']])}")
    else:
        print(f"\n📊 Cache Attuale: Vuota (nessun database)")
    
    print(f"\n💡 Comandi Disponibili:")
    print(f"   → Backup: python3 cache_backup_manager.py backup")
    print(f"   → Lista: python3 cache_backup_manager.py list")
    print(f"   → Ripristino: python3 cache_backup_manager.py restore <nome>")
    print(f"   → Pulizia sicura: python3 cache_safe_cleanup.py")
    
    return True

if __name__ == "__main__":
    print("🧪 Test Sistema Backup Cache Translation Memory")
    print("=" * 50)
    
    # Test sistema backup
    test_success = test_cache_backup_system()
    
    if test_success:
        print(f"\n🎉 SISTEMA BACKUP FUNZIONANTE")
        
        # Test integrazione
        test_cache_integration()
        
        print(f"\n✅ SISTEMA PRONTO PER L'USO:")
        print(f"   → Backup automatico prima delle pulizie")
        print(f"   → Ripristino sicuro in caso di problemi")
        print(f"   → Gestione completa della cache")
    else:
        print(f"\n❌ SISTEMA BACKUP NON FUNZIONANTE")
        print(f"   → Verificare implementazione")
        
    print(f"\n📋 WORKFLOW CONSIGLIATO:")
    print(f"   1. python3 cache_backup_manager.py backup --name pre_migration")
    print(f"   2. python3 cache_safe_cleanup.py")
    print(f"   3. [usa sistema con cache separato per lingua]")
    print(f"   4. python3 cache_backup_manager.py restore pre_migration  # se necessario")