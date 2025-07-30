#!/usr/bin/env python3
"""
Cache Safe Cleanup - Pulizia sicura della cache con backup automatico
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from cache_backup_manager import CacheBackupManager
from translation_memory import TranslationMemory
from pathlib import Path
from datetime import datetime
import click

def safe_cache_cleanup(create_backup: bool = True, backup_name: str = None) -> bool:
    """
    Pulizia sicura della cache con backup automatico
    
    Args:
        create_backup: Se creare backup prima della pulizia
        backup_name: Nome custom per il backup
        
    Returns:
        True se pulizia completata con successo
    """
    print("🧹 Pulizia Sicura Cache Translation Memory")
    print("=" * 45)
    
    manager = CacheBackupManager()
    
    # Verifica esistenza cache
    if not manager.db_path.exists():
        print("ℹ️  Nessuna cache esistente da pulire")
        return True
    
    # Analizza cache attuale
    tm = TranslationMemory()
    stats_before = tm.get_statistics()
    tm.close()
    
    print(f"📊 Cache Attuale:")
    print(f"   → Traduzioni: {stats_before['total_translations']}")
    print(f"   → Lingue: {', '.join([lang for lang, _ in stats_before['top_languages']])}")
    print(f"   → Termini: {stats_before['total_terms']}")
    
    if stats_before['total_translations'] == 0:
        print("ℹ️  Cache già vuota, pulizia non necessaria")
        return True
    
    # Crea backup se richiesto
    backup_path = None
    if create_backup:
        if backup_name is None:
            backup_name = f"pre_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n💾 Creazione backup: {backup_name}")
        backup_path = manager.create_backup(backup_name)
        
        if not backup_path:
            print("❌ Backup fallito - PULIZIA ANNULLATA per sicurezza")
            return False
        
        print(f"✅ Backup creato: {Path(backup_path).name}")
    
    # Chiedi conferma
    print(f"\n⚠️  ATTENZIONE: La pulizia eliminerà TUTTE le traduzioni dalla cache")
    if backup_path:
        print(f"✅ Backup disponibile per ripristino: {backup_name}")
    else:
        print("❌ NESSUN BACKUP - Le traduzioni verranno perse definitivamente")
    
    response = input(f"\n❓ Confermi pulizia cache? (y/N): ")
    if response.lower() != 'y':
        print("❌ Pulizia annullata")
        return False
    
    # Esegui pulizia
    try:
        tm = TranslationMemory()
        
        # Pulisci solo traduzioni, mantieni terminologia e regole
        tm.conn.execute("DELETE FROM translations")
        tm.conn.commit()
        
        # Verifica pulizia
        stats_after = tm.get_statistics()
        tm.close()
        
        print(f"\n✅ PULIZIA COMPLETATA:")
        print(f"   → Traduzioni rimosse: {stats_before['total_translations']}")
        print(f"   → Traduzioni attuali: {stats_after['total_translations']}")
        print(f"   → Terminologia conservata: {stats_after['total_terms']} termini")
        print(f"   → Regole conservate: {stats_after['active_rules']} regole")
        
        if backup_path:
            print(f"\n💾 BACKUP DISPONIBILE:")
            print(f"   → Nome: {backup_name}")
            print(f"   → Per ripristinare: python3 cache_backup_manager.py restore {backup_name}")
        
        print(f"\n🎯 CACHE PRONTA:")
        print(f"   → Sistema anti-contaminazione attivo")
        print(f"   → Cache separato per ogni lingua")
        print(f"   → Traduzioni future saranno pure e accurate")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante pulizia: {e}")
        
        if backup_path:
            print(f"💡 Ripristina backup con: python3 cache_backup_manager.py restore {backup_name}")
        
        return False

@click.command()
@click.option('--no-backup', is_flag=True, help='Non creare backup (PERICOLOSO)')
@click.option('--backup-name', '-n', help='Nome custom per il backup')
@click.option('--yes', '-y', is_flag=True, help='Conferma automatica (usa con cautela)')
def main(no_backup: bool, backup_name: str, yes: bool):
    """Pulizia sicura della cache Translation Memory con backup automatico"""
    
    create_backup = not no_backup
    
    if no_backup and not yes:
        click.echo("⚠️  ATTENZIONE: --no-backup eliminerà definitivamente le traduzioni!")
        response = input("Confermi operazione senza backup? (y/N): ")
        if response.lower() != 'y':
            click.echo("❌ Operazione annullata")
            return
    
    success = safe_cache_cleanup(create_backup, backup_name)
    
    if success:
        click.echo("\n🎉 PULIZIA SICURA COMPLETATA")  
        if create_backup:
            click.echo("💡 Backup creato per sicurezza")
            click.echo("📋 Lista backup: python3 cache_backup_manager.py list")
    else:
        click.echo("\n❌ PULIZIA FALLITA")
        click.echo("💡 Cache non modificata")

if __name__ == '__main__':
    main()