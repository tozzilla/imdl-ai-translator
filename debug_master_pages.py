#!/usr/bin/env python3
"""
Debug script per analizzare le master pages IDML e i numeri di pagina dinamici
"""

import sys
sys.path.append('src')

from idml_processor import IDMLProcessor
import os

def analyze_idml_structure(idml_file):
    """Analizza la struttura completa di un file IDML"""
    print(f"🔍 Analisi struttura IDML: {idml_file}")
    
    processor = IDMLProcessor(idml_file)
    processor.load_idml()
    
    print("\n📁 File contenuti nel package IDML:")
    for file_info in processor.idml_package.infolist():
        print(f"   {file_info.filename}")
    
    # Cerca file master pages
    master_files = []
    for file_info in processor.idml_package.infolist():
        if 'master' in file_info.filename.lower() or 'MasterSpreads' in file_info.filename:
            master_files.append(file_info.filename)
    
    print(f"\n📋 File Master Pages trovati: {len(master_files)}")
    for master_file in master_files:
        print(f"   {master_file}")
        
        # Leggi contenuto master page
        try:
            content = processor.idml_package.read(master_file)
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Cerca pattern di numerazione pagine
            page_number_patterns = [
                '<#>',  # Marker pagina corrente
                'CurrentPageNumber',
                'PageNumberType',
                'NextPageNumber',
                'PreviousPageNumber'
            ]
            
            found_patterns = []
            for pattern in page_number_patterns:
                if pattern in content:
                    found_patterns.append(pattern)
            
            if found_patterns:
                print(f"      🔢 Pattern numerazione trovati: {found_patterns}")
            
            # Cerca text frame con contenuto
            if 'TextFrame' in content:
                import re
                # Conta text frame
                frame_count = len(re.findall(r'<TextFrame[^>]*>', content))
                print(f"      📝 Text frame: {frame_count}")
                
                # Cerca contenuto testo sospetto
                content_matches = re.findall(r'<Content[^>]*>([^<]*)</Content>', content)
                if content_matches:
                    print(f"      📄 Contenuti trovati:")
                    for i, match in enumerate(content_matches[:5]):  # Solo primi 5
                        if match.strip():
                            print(f"         {i+1}. '{match.strip()}'")
                else:
                    print("      ℹ️ Nessun Content element trovato")
                    # Cerca altri pattern
                    if 'Content' in content:
                        print("      🔍 Content trovato nel testo ma non corrispondente al pattern")
                        # Mostra parte del contenuto per debug
                        print(f"      📄 Prime 500 char: {content[:500]}")
            
        except Exception as e:
            print(f"      ❌ Errore lettura: {e}")
    
    processor.close()

if __name__ == "__main__":
    # Usa il file IDML disponibile (escludendo file nascosti)
    idml_files = [f for f in os.listdir('.') if f.endswith('.idml') and not f.startswith('.')]
    
    print(f"📁 File IDML trovati: {idml_files}")
    
    if idml_files:
        for idml_file in idml_files:
            try:
                analyze_idml_structure(idml_file)
                break  # Se uno funziona, stop
            except Exception as e:
                print(f"❌ Errore con {idml_file}: {e}")
                continue
    else:
        print("❌ Nessun file IDML valido trovato nella directory corrente")