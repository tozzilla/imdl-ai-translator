"""
Test per TextExtractor
"""

import pytest
from xml.etree import ElementTree as ET
from src.text_extractor import TextExtractor


class TestTextExtractor:
    
    def setup_method(self):
        """Setup per ogni test"""
        self.extractor = TextExtractor()
    
    def test_init(self):
        """Test inizializzazione"""
        assert self.extractor.text_segments == []
        assert self.extractor.text_mapping == {}
    
    def test_is_translatable_text_valid(self):
        """Test riconoscimento testo valido per traduzione"""
        valid_texts = [
            "Hello world",
            "Questo è un testo normale",
            "Text with numbers 123 inside",
            "Mixed content: text & symbols!"
        ]
        
        for text in valid_texts:
            assert self.extractor._is_translatable_text(text)
    
    def test_is_translatable_text_invalid(self):
        """Test riconoscimento testo non valido per traduzione"""
        invalid_texts = [
            "",
            "   ",
            "123",
            "!@#$%",
            "CODE_ABC",
            "ID123",
            "https://example.com",
            "www.example.com",
            "user@example.com",
            "test@domain.com"
        ]
        
        for text in invalid_texts:
            assert not self.extractor._is_translatable_text(text)
    
    def test_clean_text_for_translation(self):
        """Test pulizia testo per traduzione"""
        # Testo con spazi multipli
        dirty_text = "  Hello    world  \n  test  "
        clean_text = self.extractor._clean_text_for_translation(dirty_text)
        assert clean_text == "Hello world test"
        
        # Testo normale
        normal_text = "Normal text"
        assert self.extractor._clean_text_for_translation(normal_text) == normal_text
    
    def test_find_text_elements_simple(self):
        """Test estrazione elementi testo da XML semplice"""
        xml_content = """
        <root>
            <element1>Text content 1</element1>
            <element2>Text content 2</element2>
        </root>
        """
        root = ET.fromstring(xml_content.strip())
        
        text_elements = self.extractor._find_text_elements(root)
        
        assert len(text_elements) == 2
        assert any(elem['text'] == 'Text content 1' for elem in text_elements)
        assert any(elem['text'] == 'Text content 2' for elem in text_elements)
    
    def test_find_text_elements_with_tail(self):
        """Test estrazione elementi con tail text"""
        xml_content = """
        <root>
            <element1>Direct text</element1>Tail text
            <element2>Another text</element2>
        </root>
        """
        root = ET.fromstring(xml_content.strip())
        
        text_elements = self.extractor._find_text_elements(root)
        
        # Dovrebbe trovare sia il testo diretto che il tail
        texts = [elem['text'] for elem in text_elements]
        assert 'Direct text' in texts
        assert 'Tail text' in texts
        assert 'Another text' in texts
    
    def test_extract_text_segments_from_story(self):
        """Test estrazione segmenti da una story"""
        xml_content = """
        <Story>
            <StoryPreference/>
            <Content>
                <CharacterStyleRange>
                    <Content>Hello world!</Content>
                </CharacterStyleRange>
                <Br/>
                <CharacterStyleRange>
                    <Content>This is a test.</Content>
                </CharacterStyleRange>
            </Content>
        </Story>
        """
        root = ET.fromstring(xml_content.strip())
        
        segments = self.extractor._extract_text_segments_from_story(root, "test_story")
        
        # Filtra solo i segmenti con testo valido
        valid_segments = [s for s in segments if self.extractor._is_translatable_text(s['original_text'])]
        
        assert len(valid_segments) >= 2
        texts = [s['original_text'] for s in valid_segments]
        assert 'Hello world!' in texts
        assert 'This is a test.' in texts
    
    def test_prepare_for_translation(self):
        """Test preparazione segmenti per traduzione"""
        segments = [
            {'original_text': '  Hello world  '},
            {'original_text': 'Test   text'},
            {'original_text': 'Normal text'}
        ]
        
        prepared_texts = self.extractor.prepare_for_translation(segments)
        
        assert len(prepared_texts) == 3
        assert prepared_texts[0] == 'Hello world'
        assert prepared_texts[1] == 'Test text'
        assert prepared_texts[2] == 'Normal text'
    
    def test_map_translations_to_segments(self):
        """Test mapping traduzioni a segmenti"""
        segments = [
            {'story_name': 'story1', 'original_text': 'Text 1'},
            {'story_name': 'story1', 'original_text': 'Text 2'},
            {'story_name': 'story2', 'original_text': 'Text 3'}
        ]
        
        translations = ['Testo 1', 'Testo 2', 'Testo 3']
        
        story_translations = self.extractor.map_translations_to_segments(segments, translations)
        
        assert 'story1' in story_translations
        assert 'story2' in story_translations
        assert len(story_translations['story1']) == 2
        assert len(story_translations['story2']) == 1
        assert story_translations['story1'] == ['Testo 1', 'Testo 2']
        assert story_translations['story2'] == ['Testo 3']
    
    def test_map_translations_wrong_count(self):
        """Test errore con numero sbagliato di traduzioni"""
        segments = [{'story_name': 'story1', 'original_text': 'Text 1'}]
        translations = ['Testo 1', 'Testo 2']  # Troppi
        
        with pytest.raises(ValueError, match="Numero di segmenti"):
            self.extractor.map_translations_to_segments(segments, translations)
    
    def test_get_translation_stats(self):
        """Test calcolo statistiche"""
        segments = [
            {'character_count': 10, 'word_count': 2, 'story_name': 'story1'},
            {'character_count': 15, 'word_count': 3, 'story_name': 'story1'},
            {'character_count': 20, 'word_count': 4, 'story_name': 'story2'}
        ]
        
        stats = self.extractor.get_translation_stats(segments)
        
        assert stats['total_segments'] == 3
        assert stats['total_characters'] == 45
        assert stats['total_words'] == 9
        assert stats['stories_count'] == 2
        assert stats['avg_chars_per_segment'] == 15
    
    def test_get_translation_stats_empty(self):
        """Test statistiche con lista vuota"""
        stats = self.extractor.get_translation_stats([])
        
        assert stats['total_segments'] == 0
        assert stats['total_characters'] == 0
        assert stats['total_words'] == 0
        assert stats['stories_count'] == 0
        assert stats['avg_chars_per_segment'] == 0


if __name__ == '__main__':
    pytest.main([__file__])