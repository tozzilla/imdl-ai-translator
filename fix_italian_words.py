#!/usr/bin/env python3
"""
Script per correggere manualmente le parole italiane rimaste nel file tradotto
"""

import os
import zipfile
import tempfile
import shutil
from pathlib import Path
import re


def fix_italian_words_in_idml(idml_path):
    """
    Corregge le parole italiane rimaste in un file IDML tradotto
    
    Args:
        idml_path: Path del file IDML da correggere
    """
    
    # Definisci le sostituzioni
    replacements = {
        # Materiali
        '>LEGNO<': '>HOLZ<',
        '>legno<': '>Holz<',
        '>CALCESTRUZZO<': '>BETON<',
        '>calcestruzzo<': '>Beton<',
        '>ACCIAIO<': '>STAHL<',
        '>acciaio<': '>Stahl<',
        
        # Verbi
        '>EVITARE<': '>VERMEIDEN<',
        '>evitare<': '>vermeiden<',
        '>VERIFICARE<': '>PRÜFEN<',
        '>verificare<': '>prüfen<',
        '>UTILIZZARE<': '>VERWENDEN<',
        '>utilizzare<': '>verwenden<',
        '>SEGUIRE<': '>FOLGEN<',
        '>seguire<': '>folgen<',
        
        # Termini tecnici
        '>SISTEMA<': '>SYSTEM<',
        '>sistema<': '>System<',
        '>ELEMENTI<': '>ELEMENTE<',
        '>elementi<': '>Elemente<',
        '>DISPOSITIVO<': '>GERÄT<',
        '>dispositivo<': '>Gerät<',
        '>MONTAGGIO<': '>MONTAGE<',
        '>montaggio<': '>Montage<',
        '>FISSAGGIO<': '>BEFESTIGUNG<',
        '>fissaggio<': '>Befestigung<',
        '>ANCORAGGIO<': '>VERANKERUNG<',
        '>ancoraggio<': '>Verankerung<',
        
        # Preposizioni e articoli
        '>della<': '>der<',
        '>delle<': '>der<',
        '>dello<': '>des<',
        '>negli<': '>in den<',
        '>nelle<': '>in den<',
        '>sulla<': '>auf der<',
        '>sulle<': '>auf den<',
        '>con<': '>mit<',
        '>per<': '>für<',
        '>una<': '>eine<',
        '>uno<': '>ein<',
        '>nel<': '>im<',
        '>nella<': '>in der<',
        
        # Altri termini comuni
        '>INSTALLAZIONE<': '>INSTALLATION<',
        '>installazione<': '>Installation<',
        '>SICUREZZA<': '>SICHERHEIT<',
        '>sicurezza<': '>Sicherheit<',
        '>MANUALE<': '>HANDBUCH<',
        '>manuale<': '>Handbuch<',
        '>PROTEZIONE<': '>SCHUTZ<',
        '>protezione<': '>Schutz<',
        '>EDIZIONE<': '>AUSGABE<',
        '>edizione<': '>Ausgabe<',
        
        # Date
        '>Giugno<': '>Juni<',
        '>giugno<': '>Juni<',
        '>Luglio<': '>Juli<',
        '>luglio<': '>Juli<',
        
        # Riferimenti pagine
        '>pag. ': '>S. ',
        '>pag.': '>S.',
    }
    
    # Crea directory temporanea
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        extract_path = temp_path / "extracted"
        extract_path.mkdir()
        
        # Estrai il file IDML
        print(f"📂 Estrazione {idml_path}...")
        with zipfile.ZipFile(idml_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Trova tutti i file Story XML
        stories_path = extract_path / "Stories"
        if not stories_path.exists():
            print("❌ Cartella Stories non trovata!")
            return False
            
        xml_files = list(stories_path.glob("*.xml"))
        print(f"📄 Trovati {len(xml_files)} file XML da processare")
        
        corrections_count = 0
        
        # Processa ogni file XML
        for xml_file in xml_files:
            if xml_file.name.startswith('._'):  # Skip macOS metadata files
                continue
                
            try:
                # Leggi il contenuto
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Applica le sostituzioni
                for old_text, new_text in replacements.items():
                    if old_text in content:
                        content = content.replace(old_text, new_text)
                        corrections_count += 1
                        
                # Scrivi solo se ci sono stati cambiamenti
                if content != original_content:
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"🔧 Corretto: {xml_file.name}")
                    
            except Exception as e:
                print(f"❌ Errore processando {xml_file}: {e}")
        
        # Crea il nuovo file IDML
        print(f"📦 Creazione nuovo file IDML...")
        backup_path = idml_path.replace('.idml', '_backup.idml')
        
        # Backup del file originale
        shutil.copy2(idml_path, backup_path)
        print(f"💾 Backup salvato: {backup_path}")
        
        # Crea il nuovo IDML
        with zipfile.ZipFile(idml_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    if file.startswith('._'):  # Skip macOS metadata
                        continue
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, extract_path)
                    zip_out.write(file_path, arc_path)
        
        print(f"✅ Correzioni applicate: {corrections_count}")
        print(f"🎉 File corretto salvato: {idml_path}")
        return True


if __name__ == "__main__":
    # Correggi il file Skyfix-Z_de.idml
    idml_file = "Skyfix-Z_de.idml"
    
    if not os.path.exists(idml_file):
        print(f"❌ File {idml_file} non trovato!")
        exit(1)
    
    success = fix_italian_words_in_idml(idml_file)
    
    if success:
        print("\n🔍 Verifica delle correzioni...")
        # Verifica rapida
        os.system(f"python -c \"import zipfile; z=zipfile.ZipFile('{idml_file}'); content=''.join([z.read(f).decode('utf-8', errors='ignore') for f in z.namelist() if 'Stories/' in f and f.endswith('.xml')]); print('❌ Ancora parole italiane:' if any(w in content for w in ['LEGNO', 'ACCIAIO', 'CALCESTRUZZO', 'EVITARE']) else '✅ Parole italiane corrette!')\"")
    else:
        print("❌ Correzione fallita!")