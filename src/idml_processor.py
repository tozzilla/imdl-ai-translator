"""
IDML Processor - Gestisce l'apertura, manipolazione e salvataggio di file IDML
"""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from simple_idml import idml


class IDMLProcessor:
    """Classe per processare file IDML di InDesign"""
    
    def __init__(self, idml_path: str):
        """
        Inizializza il processor con il path al file IDML
        
        Args:
            idml_path: Path al file IDML da processare
        """
        self.idml_path = Path(idml_path)
        self.idml_package = None
        self.stories_data = {}
        self.temp_dir = None
        
        if not self.idml_path.exists():
            raise FileNotFoundError(f"File IDML non trovato: {idml_path}")
            
    def load_idml(self) -> None:
        """Carica il file IDML in memoria"""
        try:
            self.idml_package = idml.IDMLPackage(str(self.idml_path))
            self._extract_stories()
        except Exception as e:
            raise RuntimeError(f"Errore nel caricamento IDML: {e}")
    
    def _extract_stories(self) -> None:
        """Estrae le stories (contenuti testuali) dal file IDML"""
        stories_list = self.idml_package.stories
        
        for story_path in stories_list:
            try:
                # Ottieni il contenuto della story usando il path
                story_content = self.idml_package.read(story_path)
                if isinstance(story_content, bytes):
                    story_content = story_content.decode('utf-8')
                
                # Parse XML content
                story_root = ET.fromstring(story_content)
                self.stories_data[story_path] = {
                    'root': story_root,
                    'original_content': story_content
                }
            except (ET.ParseError, Exception) as e:
                print(f"Warning: Errore parsing story {story_path}: {e}")
                continue
    
    def get_text_content(self) -> Dict[str, List[str]]:
        """
        Estrae tutto il contenuto testuale dalle stories
        
        Returns:
            Dizionario con nome story -> lista di testi
        """
        text_content = {}
        
        for story_name, story_data in self.stories_data.items():
            story_root = story_data['root']
            texts = []
            
            # Cerca tutti gli elementi che contengono testo
            for elem in story_root.iter():
                if elem.text and elem.text.strip():
                    texts.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    texts.append(elem.tail.strip())
            
            if texts:
                text_content[story_name] = texts
                
        return text_content
    
    def replace_text_content(self, translations: Dict[str, List[str]]) -> None:
        """
        Sostituisce il contenuto testuale con le traduzioni
        
        Args:
            translations: Dizionario story_name -> lista traduzioni
        """
        for story_name, translated_texts in translations.items():
            if story_name not in self.stories_data:
                continue
                
            story_root = self.stories_data[story_name]['root']
            text_elements = []
            
            # Raccoglie tutti gli elementi con testo
            for elem in story_root.iter():
                if elem.text and elem.text.strip():
                    text_elements.append((elem, 'text'))
                if elem.tail and elem.tail.strip():
                    text_elements.append((elem, 'tail'))
            
            # Sostituisce i testi con le traduzioni
            for i, (elem, attr_type) in enumerate(text_elements):
                if i < len(translated_texts):
                    if attr_type == 'text':
                        elem.text = translated_texts[i]
                    else:
                        elem.tail = translated_texts[i]
    
    def save_translated_idml(self, output_path: str) -> None:
        """
        Salva il file IDML tradotto
        
        Args:
            output_path: Path dove salvare il file tradotto
        """
        if not self.idml_package:
            raise RuntimeError("IDML non caricato. Chiamare load_idml() prima.")
        
        # Aggiorna le stories nel package con il contenuto tradotto
        for story_path, story_data in self.stories_data.items():
            updated_xml = ET.tostring(story_data['root'], encoding='unicode')
            # Aggiorna il file nel package ZIP
            self.idml_package.writestr(story_path, updated_xml)
        
        # Salva il package modificato
        self.idml_package.save(output_path)
    
    def get_document_info(self) -> Dict[str, any]:
        """
        Ottiene informazioni generali sul documento IDML
        
        Returns:
            Dizionario con informazioni del documento
        """
        if not self.idml_package:
            return {}
            
        return {
            'filename': self.idml_path.name,
            'stories_count': len(self.stories_data),
            'stories_names': list(self.stories_data.keys())
        }
    
    def close(self) -> None:
        """Chiude il processor e pulisce le risorse temporanee"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        
        self.idml_package = None
        self.stories_data = {}