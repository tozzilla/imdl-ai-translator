"""
Test per Translator
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.translator import Translator


class TestTranslator:
    
    def setup_method(self):
        """Setup per ogni test"""
        self.api_key = "test_api_key"
        self.translator = Translator(self.api_key)
    
    def test_init(self):
        """Test inizializzazione"""
        assert self.translator.model == "gpt-3.5-turbo"
        assert self.translator.rate_limit_delay == 1.0
        assert self.translator.max_retries == 3
        assert self.translator.max_tokens_per_request == 3000
    
    def test_init_custom_model(self):
        """Test inizializzazione con modello personalizzato"""
        translator = Translator(self.api_key, model="gpt-4")
        assert translator.model == "gpt-4"
    
    def test_create_batches_single_batch(self):
        """Test creazione batch con testi piccoli"""
        texts = ["Hello", "World", "Test"]
        batches = self.translator._create_batches(texts)
        
        assert len(batches) == 1
        assert batches[0] == texts
    
    def test_create_batches_multiple_batches(self):
        """Test creazione batch con testi grandi"""
        # Crea testi grandi per forzare batch multipli
        large_text = "A" * 8000  # ~2000 token stimati
        texts = [large_text, large_text, large_text]
        
        batches = self.translator._create_batches(texts)
        
        # Dovrebbe creare batch separati per evitare overflow
        assert len(batches) >= 2
    
    def test_create_translation_prompt(self):
        """Test creazione prompt per traduzione"""
        texts = ["Hello", "World"]
        target_lang = "Italian"
        
        prompt = self.translator._create_translation_prompt(texts, target_lang)
        
        assert "Italian" in prompt
        assert "Hello" in prompt
        assert "World" in prompt
        assert "2 translations" in prompt
        assert "1. Hello" in prompt
        assert "2. World" in prompt
    
    def test_create_translation_prompt_with_source_lang(self):
        """Test creazione prompt con lingua di origine"""
        texts = ["Hello"]
        target_lang = "Italian"
        source_lang = "English"
        
        prompt = self.translator._create_translation_prompt(
            texts, target_lang, source_lang
        )
        
        assert "from English" in prompt
    
    def test_create_translation_prompt_with_context(self):
        """Test creazione prompt con contesto"""
        texts = ["Hello"]
        target_lang = "Italian"
        context = "Marketing document"
        
        prompt = self.translator._create_translation_prompt(
            texts, target_lang, context=context
        )
        
        assert "Marketing document" in prompt
    
    def test_parse_translation_response_correct(self):
        """Test parsing risposta corretta"""
        response = """1. Ciao
2. Mondo
3. Test"""
        
        translations = self.translator._parse_translation_response(response, 3)
        
        assert len(translations) == 3
        assert translations[0] == "Ciao"
        assert translations[1] == "Mondo"
        assert translations[2] == "Test"
    
    def test_parse_translation_response_with_extra_text(self):
        """Test parsing risposta con testo extra"""
        response = """Here are the translations:
1. Ciao
2. Mondo

Hope this helps!"""
        
        translations = self.translator._parse_translation_response(response, 2)
        
        assert len(translations) == 2
        assert translations[0] == "Ciao"
        assert translations[1] == "Mondo"
    
    def test_parse_translation_response_missing_translations(self):
        """Test parsing con traduzioni mancanti"""
        response = "1. Ciao"  # Manca la seconda traduzione
        
        translations = self.translator._parse_translation_response(response, 2)
        
        assert len(translations) == 2
        assert translations[0] == "Ciao"
        assert translations[1] == "[TRADUZIONE MANCANTE]"
    
    def test_parse_translation_response_too_many(self):
        """Test parsing con troppe traduzioni"""
        response = """1. Ciao
2. Mondo
3. Test
4. Extra"""
        
        translations = self.translator._parse_translation_response(response, 2)
        
        assert len(translations) == 2
        assert translations[0] == "Ciao"
        assert translations[1] == "Mondo"
    
    @patch('src.translator.OpenAI')
    def test_translate_batch_success(self, mock_openai_class):
        """Test traduzione batch con successo"""
        # Mock della risposta API
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "1. Ciao\n2. Mondo"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Ricrea il translator con il mock
        translator = Translator(self.api_key)
        
        texts = ["Hello", "World"]
        translations = translator._translate_batch(texts, "Italian")
        
        assert len(translations) == 2
        assert translations[0] == "Ciao"
        assert translations[1] == "Mondo"
        
        # Verifica che l'API sia stata chiamata
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('src.translator.OpenAI')
    def test_translate_batch_retry_on_failure(self, mock_openai_class):
        """Test retry su errore API"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            Exception("API Error"),  # Primo tentativo fallisce
            Exception("API Error"),  # Secondo tentativo fallisce
            Mock(choices=[Mock(message=Mock(content="1. Ciao"))])  # Terzo succede
        ]
        mock_openai_class.return_value = mock_client
        
        translator = Translator(self.api_key)
        
        with patch('time.sleep'):  # Mock sleep per velocizzare test
            translations = translator._translate_batch(["Hello"], "Italian")
        
        assert len(translations) == 1
        assert translations[0] == "Ciao"
        assert mock_client.chat.completions.create.call_count == 3
    
    def test_get_supported_languages(self):
        """Test ottenimento lingue supportate"""
        languages = self.translator.get_supported_languages()
        
        assert isinstance(languages, dict)
        assert len(languages) > 0
        assert 'en' in languages
        assert 'it' in languages
        assert languages['en'] == 'English'
        assert languages['it'] == 'Italian'
    
    def test_estimate_cost(self):
        """Test stima costi"""
        texts = ["Hello world", "Test text"]
        estimate = self.translator.estimate_cost(texts, "Italian")
        
        assert 'estimated_input_tokens' in estimate
        assert 'estimated_output_tokens' in estimate
        assert 'estimated_total_cost_usd' in estimate
        assert estimate['estimated_input_tokens'] > 0
        assert estimate['estimated_total_cost_usd'] > 0
    
    @patch('src.translator.OpenAI')
    @patch('time.sleep')
    def test_translate_texts_empty_list(self, mock_sleep, mock_openai_class):
        """Test traduzione lista vuota"""
        translator = Translator(self.api_key)
        
        result = translator.translate_texts([], "Italian")
        
        assert result == []
        mock_sleep.assert_not_called()
    
    @patch('src.translator.OpenAI')
    @patch('time.sleep')
    def test_translate_single_text(self, mock_sleep, mock_openai_class):
        """Test traduzione testo singolo"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "1. Ciao"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        translator = Translator(self.api_key)
        
        result = translator.translate_single_text("Hello", "Italian")
        
        assert result == "Ciao"


if __name__ == '__main__':
    pytest.main([__file__])