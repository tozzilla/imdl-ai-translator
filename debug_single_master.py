#!/usr/bin/env python3
"""
Debug singola master page per capire la struttura
"""

import sys
sys.path.append('src')

from idml_processor import IDMLProcessor
import xml.etree.ElementTree as ET

def debug_single_master(idml_file, master_index=0):
    """Debug detailed master page structure"""
    print(f"🔍 Debug master page structure in: {idml_file}")
    
    processor = IDMLProcessor(idml_file)
    processor.load_idml()
    
    # Find master pages
    master_files = []
    for file_info in processor.idml_package.infolist():
        if 'MasterSpreads' in file_info.filename and file_info.filename.endswith('.xml'):
            master_files.append(file_info.filename)
    
    if not master_files:
        print("❌ No master pages found")
        return
    
    if master_index >= len(master_files):
        master_index = 0
    
    master_file = master_files[master_index]
    print(f"📄 Analyzing: {master_file}")
    
    # Read content
    content = processor.idml_package.read(master_file)
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    
    # Parse XML
    try:
        root = ET.fromstring(content)
        print(f"✅ XML parsed successfully")
        
        # Find all elements
        def remove_namespace(tag):
            return tag.split('}')[-1] if '}' in tag else tag
        
        # Count different element types
        element_types = {}
        content_elements = []
        text_frame_elements = []
        
        for element in root.iter():
            tag = remove_namespace(element.tag)
            element_types[tag] = element_types.get(tag, 0) + 1
            
            if tag == 'Content':
                content_elements.append(element)
            elif tag == 'TextFrame':
                text_frame_elements.append(element)
        
        print(f"\n📊 Element Types:")
        for tag, count in sorted(element_types.items()):
            print(f"   {tag}: {count}")
        
        print(f"\n🔍 Content Elements Found: {len(content_elements)}")
        for i, elem in enumerate(content_elements[:10]):  # Show first 10
            text_content = elem.text if elem.text else ""
            tail_content = elem.tail if elem.tail else ""
            
            print(f"   {i+1}. Text: '{text_content}' | Tail: '{tail_content}'")
            print(f"       Attributes: {dict(elem.attrib)}")
        
        print(f"\n📝 Text Frame Elements: {len(text_frame_elements)}")
        for i, frame in enumerate(text_frame_elements[:3]):  # Show first 3
            print(f"   Frame {i+1}:")
            print(f"       Attributes: {dict(frame.attrib)}")
            
            # Look for content inside text frame
            for child in frame.iter():
                child_tag = remove_namespace(child.tag)
                if child_tag == 'Content' and (child.text or child.tail):
                    text_content = child.text.strip() if child.text else ""
                    tail_content = child.tail.strip() if child.tail else ""
                    if text_content or tail_content:
                        print(f"           Content: '{text_content}' | Tail: '{tail_content}'")
    
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    processor.close()

if __name__ == "__main__":
    # Use the original Italian file
    idml_file = "UNICO SafeGuard Wall .idml"
    debug_single_master(idml_file, 0)  # First master page