#!/usr/bin/env python3
"""
Debug script to analyze IDML story extraction and identify missed Content elements.

This script:
1. Loads IDML using the existing IDMLProcessor
2. Lists all stories found by the processor
3. Manually checks what XML files contain Content elements in the IDML archive
4. Compares the two lists to identify missed files
5. Specifically looks for BackingStory.xml and checks its content
"""

import os
import zipfile
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Dict, List, Set, Tuple

# Import existing processor
from src.idml_processor import IDMLProcessor
from src.text_extractor import TextExtractor


def analyze_idml_extraction(idml_path: str) -> None:
    """
    Comprehensive analysis of IDML extraction process
    
    Args:
        idml_path: Path to the IDML file to analyze
    """
    print(f"🔍 Analyzing IDML extraction for: {idml_path}")
    print("=" * 80)
    
    # Step 1: Load with existing IDMLProcessor
    print("\n1️⃣ LOADING WITH IDMLProcessor")
    print("-" * 40)
    
    try:
        processor = IDMLProcessor(idml_path)
        processor.load_idml()
        
        processor_stories = set(processor.stories_data.keys())
        print(f"Stories found by IDMLProcessor: {len(processor_stories)}")
        for story in sorted(processor_stories):
            print(f"  ✓ {story}")
            
    except Exception as e:
        print(f"❌ Error loading with IDMLProcessor: {e}")
        return
    
    # Step 2: Manual analysis of IDML archive
    print(f"\n2️⃣ MANUAL ANALYSIS OF IDML ARCHIVE")
    print("-" * 40)
    
    archive_stories = analyze_idml_archive(idml_path)
    print(f"Stories found in archive: {len(archive_stories)}")
    for story in sorted(archive_stories):
        print(f"  ✓ {story}")
    
    # Step 3: Compare the two lists
    print(f"\n3️⃣ COMPARISON ANALYSIS")
    print("-" * 40)
    
    missed_stories = archive_stories - processor_stories
    extra_stories = processor_stories - archive_stories
    
    if missed_stories:
        print(f"🚨 MISSED STORIES ({len(missed_stories)}):")
        for story in sorted(missed_stories):
            print(f"  ❌ {story}")
    else:
        print("✅ No missed stories detected")
    
    if extra_stories:
        print(f"⚠️  EXTRA STORIES in processor ({len(extra_stories)}):")
        for story in sorted(extra_stories):
            print(f"  ⚠️  {story}")
    else:
        print("✅ No extra stories in processor")
    
    # Step 4: Specific BackingStory.xml analysis
    print(f"\n4️⃣ BackingStory.xml ANALYSIS")
    print("-" * 40)
    
    analyze_backing_story(idml_path)
    
    # Step 5: Content element analysis
    print(f"\n5️⃣ CONTENT ELEMENTS ANALYSIS")
    print("-" * 40)
    
    analyze_content_elements(idml_path, processor_stories, archive_stories)
    
    # Step 6: Test text extraction
    print(f"\n6️⃣ TEXT EXTRACTION TEST")
    print("-" * 40)
    
    test_text_extraction(processor)


def analyze_idml_archive(idml_path: str) -> Set[str]:
    """
    Manually analyze the IDML archive to find all XML files with Content elements
    
    Args:
        idml_path: Path to IDML file
        
    Returns:
        Set of story file paths that contain Content elements
    """
    stories_with_content = set()
    
    try:
        with zipfile.ZipFile(idml_path, 'r') as archive:
            # Get all XML files in the archive
            xml_files = [f for f in archive.namelist() if f.endswith('.xml')]
            
            print(f"Total XML files in archive: {len(xml_files)}")
            
            for xml_file in xml_files:
                try:
                    content = archive.read(xml_file)
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    
                    # Parse and check for Content elements
                    root = ET.fromstring(content)
                    content_elements = find_content_elements(root)
                    
                    if content_elements:
                        stories_with_content.add(xml_file)
                        print(f"  📄 {xml_file}: {len(content_elements)} Content elements")
                        
                        # Show first few content samples
                        for i, (elem, text) in enumerate(content_elements[:3]):
                            preview = text[:50] + "..." if len(text) > 50 else text
                            print(f"    📝 {preview}")
                        
                        if len(content_elements) > 3:
                            print(f"    ... and {len(content_elements) - 3} more")
                    
                except ET.ParseError as e:
                    print(f"  ⚠️  XML parse error in {xml_file}: {e}")
                except Exception as e:
                    print(f"  ❌ Error processing {xml_file}: {e}")
                    
    except Exception as e:
        print(f"❌ Error analyzing archive: {e}")
    
    return stories_with_content


def find_content_elements(root: ET.Element) -> List[Tuple[ET.Element, str]]:
    """
    Find all Content elements in an XML tree that contain text
    
    Args:
        root: Root XML element
        
    Returns:
        List of (element, text) tuples for Content elements with text
    """
    content_elements = []
    
    def remove_namespace(tag):
        return tag.split('}')[-1] if '}' in tag else tag
    
    for elem in root.iter():
        elem_tag = remove_namespace(elem.tag)
        
        if elem_tag == 'Content':
            if elem.text and elem.text.strip():
                content_elements.append((elem, elem.text.strip()))
            if elem.tail and elem.tail.strip():
                content_elements.append((elem, elem.tail.strip()))
    
    return content_elements


def analyze_backing_story(idml_path: str) -> None:
    """
    Specific analysis of BackingStory.xml file
    
    Args:
        idml_path: Path to IDML file
    """
    try:
        with zipfile.ZipFile(idml_path, 'r') as archive:
            backing_story_files = [f for f in archive.namelist() if 'BackingStory.xml' in f]
            
            if not backing_story_files:
                print("❌ No BackingStory.xml found in archive")
                return
            
            for backing_file in backing_story_files:
                print(f"📄 Found: {backing_file}")
                
                try:
                    content = archive.read(backing_file)
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    
                    root = ET.fromstring(content)
                    content_elements = find_content_elements(root)
                    
                    print(f"  📊 Content elements: {len(content_elements)}")
                    
                    if content_elements:
                        print("  📝 Content samples:")
                        for i, (elem, text) in enumerate(content_elements[:5]):
                            preview = text[:80] + "..." if len(text) > 80 else text
                            print(f"    {i+1}. {preview}")
                        
                        if len(content_elements) > 5:
                            print(f"  ... and {len(content_elements) - 5} more")
                    else:
                        print("  ✅ No translatable content found")
                        
                        # Show structure for debugging
                        print("  🔍 XML structure:")
                        show_xml_structure(root, max_depth=3)
                    
                except ET.ParseError as e:
                    print(f"  ❌ XML parse error: {e}")
                except Exception as e:
                    print(f"  ❌ Processing error: {e}")
                    
    except Exception as e:
        print(f"❌ Error analyzing BackingStory: {e}")


def show_xml_structure(element: ET.Element, indent: str = "", max_depth: int = 3, current_depth: int = 0) -> None:
    """
    Show XML structure for debugging
    
    Args:
        element: XML element to analyze
        indent: Current indentation
        max_depth: Maximum depth to show
        current_depth: Current depth in recursion
    """
    if current_depth >= max_depth:
        return
    
    def remove_namespace(tag):
        return tag.split('}')[-1] if '}' in tag else tag
    
    tag = remove_namespace(element.tag)
    attrs = list(element.attrib.keys())[:3]  # Show first 3 attributes
    attr_str = f" ({', '.join(attrs)})" if attrs else ""
    
    text_preview = ""
    if element.text and element.text.strip():
        preview = element.text.strip()[:30]
        text_preview = f" → '{preview}...'" if len(element.text.strip()) > 30 else f" → '{preview}'"
    
    print(f"{indent}{tag}{attr_str}{text_preview}")
    
    # Show only first few children to avoid spam
    children = list(element)[:5]
    for child in children:
        show_xml_structure(child, indent + "  ", max_depth, current_depth + 1)
    
    if len(element) > 5:
        print(f"{indent}  ... and {len(element) - 5} more children")


def analyze_content_elements(idml_path: str, processor_stories: Set[str], archive_stories: Set[str]) -> None:
    """
    Analyze Content elements in detail
    
    Args:
        idml_path: Path to IDML file
        processor_stories: Stories found by processor
        archive_stories: Stories found in archive
    """
    total_content_elements = 0
    translatable_content = 0
    
    try:
        # Initialize text extractor for filtering
        extractor = TextExtractor()
        
        with zipfile.ZipFile(idml_path, 'r') as archive:
            for story_file in sorted(archive_stories):
                try:
                    content = archive.read(story_file)
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    
                    root = ET.fromstring(content)
                    content_elements = find_content_elements(root)
                    total_content_elements += len(content_elements)
                    
                    # Count translatable content
                    story_translatable = 0
                    for elem, text in content_elements:
                        if extractor._is_translatable_text(text):
                            story_translatable += 1
                    
                    translatable_content += story_translatable
                    
                    # Show details for missed stories
                    if story_file in (archive_stories - processor_stories):
                        print(f"🚨 MISSED: {story_file}")
                        print(f"  📊 Total Content: {len(content_elements)}, Translatable: {story_translatable}")
                        
                        if story_translatable > 0:
                            print("  📝 Translatable samples:")
                            sample_count = 0
                            for elem, text in content_elements:
                                if extractor._is_translatable_text(text) and sample_count < 3:
                                    preview = text[:60] + "..." if len(text) > 60 else text
                                    print(f"    • {preview}")
                                    sample_count += 1
                    
                except Exception as e:
                    print(f"  ❌ Error analyzing {story_file}: {e}")
    
    except Exception as e:
        print(f"❌ Error in content analysis: {e}")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total Content elements in archive: {total_content_elements}")
    print(f"  Translatable Content elements: {translatable_content}")
    print(f"  Stories in processor: {len(processor_stories)}")
    print(f"  Stories in archive: {len(archive_stories)}")


def test_text_extraction(processor: IDMLProcessor) -> None:
    """
    Test the actual text extraction process
    
    Args:
        processor: Loaded IDMLProcessor instance
    """
    try:
        # Extract text using current method
        text_content = processor.get_text_content()
        
        print(f"Stories with extracted text: {len(text_content)}")
        total_texts = sum(len(texts) for texts in text_content.values())
        print(f"Total text segments extracted: {total_texts}")
        
        # Show samples
        print("\n📝 EXTRACTED TEXT SAMPLES:")
        sample_count = 0
        for story_name, texts in text_content.items():
            if sample_count >= 10:  # Limit samples
                break
            
            print(f"\n  📄 {story_name} ({len(texts)} segments):")
            for i, text in enumerate(texts[:3]):  # First 3 from each story
                preview = text[:60] + "..." if len(text) > 60 else text
                print(f"    {i+1}. {preview}")
                sample_count += 1
            
            if len(texts) > 3:
                print(f"    ... and {len(texts) - 3} more")
        
        # Test with TextExtractor for comparison
        print(f"\n🔧 TESTING WITH TextExtractor:")
        extractor = TextExtractor()
        segments = extractor.extract_translatable_text(processor.stories_data)
        
        print(f"Segments found by TextExtractor: {len(segments)}")
        
        if segments:
            print("📝 TextExtractor samples:")
            for i, segment in enumerate(segments[:5]):
                preview = segment['original_text'][:60] + "..." if len(segment['original_text']) > 60 else segment['original_text']
                print(f"  {i+1}. {preview}")
                print(f"     Story: {segment.get('story_name', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error in text extraction test: {e}")


def main():
    """Main function"""
    import sys
    
    # Default to the RIWEGA file if no argument provided
    default_file = "RIWEGA SafeGuard Wall_Istruzioni di assemblaggio linea_rev01 Maggio2025.idml"
    
    if len(sys.argv) > 1:
        idml_file = sys.argv[1]
    else:
        # Look for RIWEGA files in current directory
        current_dir = Path(".")
        riwega_files = list(current_dir.glob("*RIWEGA*.idml"))
        
        if riwega_files:
            idml_file = str(riwega_files[0])
            print(f"🎯 Using found RIWEGA file: {idml_file}")
        elif Path(default_file).exists():
            idml_file = default_file
            print(f"🎯 Using default file: {default_file}")
        else:
            print("❌ No IDML file specified and no RIWEGA file found.")
            print("Usage: python debug_idml_extraction.py [idml_file.idml]")
            sys.exit(1)
    
    if not Path(idml_file).exists():
        print(f"❌ File not found: {idml_file}")
        sys.exit(1)
    
    try:
        analyze_idml_extraction(idml_file)
        print(f"\n✅ Analysis complete!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()