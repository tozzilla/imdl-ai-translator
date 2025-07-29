#!/usr/bin/env python3
"""
Test script per verificare la funzionalità master pages
"""

import sys
sys.path.append('src')

from idml_processor import IDMLProcessor
import os

def test_master_pages_extraction(idml_file):
    """Test extraction of master pages content"""
    print(f"🧪 Test estrazione master pages: {idml_file}")
    
    processor = IDMLProcessor(idml_file)
    processor.load_idml()
    
    # Test extraction
    master_content = processor.extract_master_pages_content()
    
    print(f"📊 Risultati:")
    print(f"   Master pages trovate: {len(master_content)}")
    
    total_translatable = 0
    total_page_numbers = 0
    
    for master_file, master_data in master_content.items():
        translatable_texts = master_data.get('translatable_texts', [])
        page_number_elements = master_data.get('page_number_elements', [])
        
        print(f"   📄 {master_file}:")
        print(f"      - Testi traducibili: {len(translatable_texts)}")
        print(f"      - Elementi numeri pagina: {len(page_number_elements)}")
        
        # Mostra alcuni testi traducibili
        for i, text_info in enumerate(translatable_texts[:3]):
            print(f"         '{text_info['content']}'")
        
        # Mostra alcuni numeri di pagina
        for i, page_info in enumerate(page_number_elements[:3]):
            print(f"         Numero pagina: '{page_info['content']}'")
        
        total_translatable += len(translatable_texts)
        total_page_numbers += len(page_number_elements)
    
    print(f"\n📈 Totali:")
    print(f"   Testi da tradurre: {total_translatable}")
    print(f"   Numeri di pagina: {total_page_numbers}")
    
    processor.close()
    return total_translatable > 0

if __name__ == "__main__":
    # Trova file IDML di test
    idml_files = [f for f in os.listdir('.') if f.endswith('.idml') and not f.startswith('.')]
    
    # Try the original Italian file first
    original_file = "UNICO SafeGuard Wall .idml"
    if original_file in idml_files:
        test_file = original_file
    elif idml_files:
        test_file = idml_files[0]
    else:
        print("❌ Nessun file IDML trovato per il test")
        sys.exit(1)
    
    print(f"📁 Usando file di test: {test_file}")
    
    success = test_master_pages_extraction(test_file)
    if success:
        print("\n✅ Test completato con successo!")
    else:
        print("\n⚠️ Nessun testo traducibile trovato nelle master pages")