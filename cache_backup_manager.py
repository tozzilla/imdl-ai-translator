#!/usr/bin/env python3
"""
Cache Backup Manager - Sistema per salvare e ripristinare cache Translation Memory
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from translation_memory import TranslationMemory
from pathlib import Path
import json
import sqlite3
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
import click

class CacheBackupManager:
    """Gestisce backup e restore della cache Translation Memory"""
    
    def __init__(self):
        self.default_dir = Path.home() / '.translate-idml'
        self.db_path = self.default_dir / 'tm.db'
        self.backup_dir = self.default_dir / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Crea backup completo della cache
        
        Args:
            backup_name: Nome del backup (opzionale, default: timestamp)
            
        Returns:
            Path del backup creato
        """
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"cache_backup_{timestamp}"
        
        backup_path = self.backup_dir / f"{backup_name}.db"
        
        if not self.db_path.exists():
            print("⚠️  Nessun database cache esistente da salvare")
            return ""
        
        # Copia database
        shutil.copy2(self.db_path, backup_path)
        
        # Crea metadata del backup
        metadata = self._collect_backup_metadata()
        metadata_path = self.backup_dir / f"{backup_name}.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Backup creato: {backup_path}")
        print(f"📊 Metadata: {metadata_path}")
        print(f"   → {metadata['total_translations']} traduzioni salvate")
        print(f"   → Lingue: {', '.join(metadata['languages'])}")
        
        return str(backup_path)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lista tutti i backup disponibili
        
        Returns:
            Lista di informazioni sui backup
        """
        backups = []
        
        for db_file in self.backup_dir.glob("*.db"):
            backup_name = db_file.stem
            metadata_file = self.backup_dir / f"{backup_name}.json"
            
            backup_info = {
                'name': backup_name,
                'db_path': str(db_file),
                'metadata_path': str(metadata_file) if metadata_file.exists() else None,
                'created': datetime.fromtimestamp(db_file.stat().st_mtime),
                'size_mb': round(db_file.stat().st_size / (1024*1024), 2)
            }
            
            # Carica metadata se disponibile
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    backup_info.update(metadata)
                except:
                    pass
            
            backups.append(backup_info)
        
        # Ordina per data di creazione (più recenti prima)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    def restore_backup(self, backup_name: str, confirm: bool = False) -> bool:
        """
        Ripristina un backup della cache
        
        Args:
            backup_name: Nome del backup da ripristinare
            confirm: Se True, non chiede conferma
            
        Returns:
            True se ripristino avvenuto con successo
        """
        backup_path = self.backup_dir / f"{backup_name}.db"
        
        if not backup_path.exists():
            print(f"❌ Backup '{backup_name}' non trovato")
            return False
        
        # Mostra info backup
        metadata_path = self.backup_dir / f"{backup_name}.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            print(f"📋 Backup da ripristinare: {backup_name}")
            print(f"   → Data: {metadata.get('backup_date', 'N/A')}")
            print(f"   → Traduzioni: {metadata.get('total_translations', 'N/A')}")
            print(f"   → Lingue: {', '.join(metadata.get('languages', []))}")
        
        # Backup attuale prima del restore (se esiste)
        current_backup = None
        if self.db_path.exists():
            current_backup = self.create_backup(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            print(f"🔄 Cache attuale salvata in: {Path(current_backup).name}")
        
        if not confirm:
            response = input(f"\n❓ Confermi il ripristino del backup '{backup_name}'? (y/N): ")
            if response.lower() != 'y':
                print("❌ Ripristino annullato")
                return False
        
        # Esegui ripristino
        try:
            if self.db_path.exists():
                self.db_path.unlink()  # Rimuovi database attuale
            
            shutil.copy2(backup_path, self.db_path)
            
            print(f"✅ Cache ripristinata da backup: {backup_name}")
            
            # Verifica ripristino
            tm = TranslationMemory()
            stats = tm.get_statistics()
            tm.close()
            
            print(f"📊 Cache ripristinata:")
            print(f"   → {stats['total_translations']} traduzioni")
            print(f"   → {len(stats['top_languages'])} lingue")
            
            return True
            
        except Exception as e:
            print(f"❌ Errore durante ripristino: {e}")
            
            # Tenta ripristino del backup precedente
            if current_backup and Path(current_backup).exists():
                try:
                    shutil.copy2(current_backup, self.db_path)
                    print("🔧 Cache precedente ripristinata")
                except:
                    print("⚠️  Impossibile ripristinare cache precedente")
            
            return False
    
    def delete_backup(self, backup_name: str, confirm: bool = False) -> bool:
        """
        Elimina un backup
        
        Args:
            backup_name: Nome backup da eliminare
            confirm: Se True, non chiede conferma
            
        Returns:
            True se eliminazione avvenuta con successo
        """
        backup_path = self.backup_dir / f"{backup_name}.db"
        metadata_path = self.backup_dir / f"{backup_name}.json"
        
        if not backup_path.exists():
            print(f"❌ Backup '{backup_name}' non trovato")
            return False
        
        if not confirm:
            response = input(f"❓ Confermi eliminazione backup '{backup_name}'? (y/N): ")
            if response.lower() != 'y':
                print("❌ Eliminazione annullata")
                return False
        
        try:
            backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            
            print(f"🗑️  Backup '{backup_name}' eliminato")
            return True
            
        except Exception as e:
            print(f"❌ Errore eliminazione: {e}")
            return False
    
    def _collect_backup_metadata(self) -> Dict[str, Any]:
        """Raccoglie metadata sul backup corrente"""
        tm = TranslationMemory(str(self.db_path))
        stats = tm.get_statistics()
        
        metadata = {
            'backup_date': datetime.now().isoformat(),
            'total_translations': stats['total_translations'],
            'total_terms': stats['total_terms'],
            'active_rules': stats['active_rules'],
            'languages': [lang for lang, _ in stats['top_languages']],
            'top_languages': stats['top_languages']
        }
        
        tm.close()
        return metadata
    
    def analyze_backup_differences(self, backup_name: str) -> Dict[str, Any]:
        """
        Analizza differenze tra backup e cache attuale
        
        Args:
            backup_name: Nome backup da confrontare
            
        Returns:
            Dizionario con le differenze
        """
        backup_path = self.backup_dir / f"{backup_name}.db"
        
        if not backup_path.exists():
            return {'error': f"Backup '{backup_name}' non trovato"}
        
        # Stats backup
        backup_tm = TranslationMemory(str(backup_path))
        backup_stats = backup_tm.get_statistics()
        backup_tm.close()
        
        # Stats attuali
        if self.db_path.exists():
            current_tm = TranslationMemory(str(self.db_path))
            current_stats = current_tm.get_statistics()
            current_tm.close()
        else:
            current_stats = {'total_translations': 0, 'total_terms': 0, 'top_languages': []}
        
        # Calcola differenze
        diff = {
            'backup_name': backup_name,
            'backup_translations': backup_stats['total_translations'],
            'current_translations': current_stats['total_translations'],
            'translation_diff': current_stats['total_translations'] - backup_stats['total_translations'],
            'backup_languages': [lang for lang, _ in backup_stats['top_languages']],
            'current_languages': [lang for lang, _ in current_stats['top_languages']],
            'added_languages': [],
            'removed_languages': []
        }
        
        # Lingue aggiunte/rimosse
        backup_langs = set(diff['backup_languages'])
        current_langs = set(diff['current_languages'])
        
        diff['added_languages'] = list(current_langs - backup_langs)
        diff['removed_languages'] = list(backup_langs - current_langs)
        
        return diff

# CLI Interface
@click.group()
def cli():
    """Cache Backup Manager - Gestione backup Translation Memory"""
    pass

@cli.command()
@click.option('--name', '-n', help='Nome del backup (default: timestamp)')
def backup(name: Optional[str]):
    """Crea backup della cache Translation Memory"""
    manager = CacheBackupManager()
    backup_path = manager.create_backup(name)
    
    if backup_path:
        click.echo(f"\n✅ Backup completato: {Path(backup_path).name}")
    else:
        click.echo("❌ Backup fallito")

@cli.command()
def list():
    """Lista tutti i backup disponibili"""
    manager = CacheBackupManager()
    backups = manager.list_backups()
    
    if not backups:
        click.echo("📂 Nessun backup trovato")
        return
    
    click.echo("📋 Backup disponibili:")
    click.echo("-" * 80)
    
    for backup in backups:
        created = backup['created'].strftime("%Y-%m-%d %H:%M:%S")
        translations = backup.get('total_translations', 'N/A')
        languages = ', '.join(backup.get('languages', []))
        size = backup['size_mb']
        
        click.echo(f"🗂️  {backup['name']}")
        click.echo(f"   Data: {created} | Traduzioni: {translations} | Lingue: {languages} | Size: {size}MB")
        click.echo()

@cli.command()
@click.argument('backup_name')
@click.option('--yes', '-y', is_flag=True, help='Conferma automatica')
def restore(backup_name: str, yes: bool):
    """Ripristina backup della cache"""
    manager = CacheBackupManager()
    success = manager.restore_backup(backup_name, confirm=yes)
    
    if success:
        click.echo("✅ Ripristino completato")
    else:
        click.echo("❌ Ripristino fallito")

@cli.command()
@click.argument('backup_name')
@click.option('--yes', '-y', is_flag=True, help='Conferma automatica')
def delete(backup_name: str, yes: bool):
    """Elimina un backup"""
    manager = CacheBackupManager()
    success = manager.delete_backup(backup_name, confirm=yes)
    
    if success:
        click.echo("✅ Backup eliminato")
    else:
        click.echo("❌ Eliminazione fallita")

@cli.command()
@click.argument('backup_name')
def diff(backup_name: str):
    """Mostra differenze tra backup e cache attuale"""
    manager = CacheBackupManager()
    differences = manager.analyze_backup_differences(backup_name)
    
    if 'error' in differences:
        click.echo(f"❌ {differences['error']}")
        return
    
    click.echo(f"📊 Differenze: {backup_name} vs Cache Attuale")
    click.echo("-" * 50)
    click.echo(f"Backup traduzioni: {differences['backup_translations']}")
    click.echo(f"Attuali traduzioni: {differences['current_translations']}")
    click.echo(f"Differenza: {differences['translation_diff']:+d}")
    
    if differences['added_languages']:
        click.echo(f"Lingue aggiunte: {', '.join(differences['added_languages'])}")
    
    if differences['removed_languages']:
        click.echo(f"Lingue rimosse: {', '.join(differences['removed_languages'])}")

if __name__ == '__main__':
    cli()