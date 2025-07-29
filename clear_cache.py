#!/usr/bin/env python3
"""
Script per cancellare la cache Translation Memory
"""

import os
from pathlib import Path
import sys

def clear_translation_memory():
    """Cancella il database Translation Memory"""
    tm_path = Path.home() / '.translate-idml' / 'tm.db'
    
    if tm_path.exists():
        try:
            os.remove(tm_path)
            print(f"✅ Translation Memory cancellata: {tm_path}")
            return True
        except Exception as e:
            print(f"❌ Errore nella cancellazione: {e}")
            return False
    else:
        print(f"ℹ️  Translation Memory non trovata in: {tm_path}")
        return False

def clear_all_caches():
    """Cancella tutte le cache del sistema"""
    cleared = False
    
    # 1. Translation Memory
    if clear_translation_memory():
        cleared = True
    
    # 2. Altri file cache se presenti
    cache_dirs = [
        Path.home() / '.translate-idml',
        Path('.') / '__pycache__',
        Path('./src') / '__pycache__'
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists() and cache_dir.name == '__pycache__':
            import shutil
            try:
                shutil.rmtree(cache_dir)
                print(f"✅ Cache Python cancellata: {cache_dir}")
                cleared = True
            except Exception as e:
                print(f"⚠️  Impossibile cancellare {cache_dir}: {e}")
    
    if cleared:
        print("\n🎉 Tutte le cache sono state cancellate!")
    else:
        print("\nℹ️  Nessuna cache da cancellare.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        clear_all_caches()
    else:
        clear_translation_memory()
        print("\nSuggerimento: usa 'python clear_cache.py --all' per cancellare tutte le cache")