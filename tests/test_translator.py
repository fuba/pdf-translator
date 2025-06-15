"""Tests for translator module."""
from unittest.mock import Mock, patch

import pytest

from pdf_translator.translator import (
    OllamaTranslator,
    OpenAITranslator,
    TranslationResult,
    TranslatorConfig,
    TranslatorFactory,
)


class TestTranslatorConfig:
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "engine": "ollama",
            "model": "gemma3:4b",
            "base_url": "http://localhost:11434/api",
            "temperature": 0.3,
            "max_tokens": 4096
        }
        config = TranslatorConfig.from_dict(config_dict)

        assert config.engine == "ollama"
        assert config.model == "gemma3:4b"
        assert config.base_url == "http://localhost:11434/api"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096

    def test_default_values(self):
        """Test default configuration values."""
        config = TranslatorConfig()

        assert config.engine == "ollama"
        assert config.model == "gemma3:4b"
        assert config.temperature == 0.3


class TestBaseTranslator:
    def test_system_prompt(self):
        """Test system prompt generation."""
        config = TranslatorConfig()
        # Use OllamaTranslator to test BaseTranslator methods
        translator = OllamaTranslator(config)

        prompt = translator.get_system_prompt(
            source_lang="en",
            target_lang="ja",
            preserve_format=True
        )

        assert "English" in prompt
        assert "Japanese" in prompt
        assert "layout" in prompt.lower()
        assert "technical terms" in prompt.lower()

    def test_prepare_text(self):
        """Test text preparation for translation."""
        config = TranslatorConfig()
        # Use OllamaTranslator to test BaseTranslator methods
        translator = OllamaTranslator(config)

        text = "This is a test.\n\nWith multiple paragraphs."
        prepared = translator.prepare_text(text)

        assert prepared == text.strip()  # Should strip whitespace


class TestOllamaTranslator:
    @patch('requests.post')
    def test_translate_success(self, mock_post):
        """Test successful translation with Ollama."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": "これはテストです。"
            }
        }
        mock_post.return_value = mock_response

        config = TranslatorConfig(
            engine="ollama",
            model="gemma3:4b",
            base_url="http://localhost:11434/api"
        )
        translator = OllamaTranslator(config)

        result = translator.translate(
            "This is a test.",
            source_lang="en",
            target_lang="ja"
        )

        assert result.translated_text == "これはテストです。"
        assert result.source_lang == "en"
        assert result.target_lang == "ja"
        assert result.success is True

        # Check API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"

        payload = call_args[1]["json"]
        assert payload["model"] == "gemma3:4b"
        assert len(payload["messages"]) == 2  # system + user

    @patch('requests.post')
    def test_translate_failure(self, mock_post):
        """Test translation failure handling."""
        mock_post.side_effect = Exception("Connection error")

        test_config_path = Path(__file__).parent / "test_config.yml"
        config_manager = ConfigManager(str(test_config_path))
        translator = OllamaTranslator(config_manager)

        result = translator.translate(
            "This is a test.",
            source_lang="en",
            target_lang="ja"
        )

        assert result.success is False
        assert result.error is not None
        assert "Connection error" in result.error

    @patch('requests.post')
    def test_batch_translate(self, mock_post):
        """Test batch translation."""
        # Mock responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {"message": {"content": "これはテスト1です。"}},
            {"message": {"content": "これはテスト2です。"}}
        ]
        mock_post.return_value = mock_response

        test_config_path = Path(__file__).parent / "test_config.yml"
        config_manager = ConfigManager(str(test_config_path))
        translator = OllamaTranslator(config_manager)

        texts = ["This is test 1.", "This is test 2."]
        results = translator.translate_batch(
            texts,
            source_lang="en",
            target_lang="ja"
        )

        assert len(results) == 2
        assert results[0].translated_text == "これはテスト1です。"
        assert results[1].translated_text == "これはテスト2です。"
        assert all(r.success for r in results)


class TestOpenAITranslator:
    @patch('openai.ChatCompletion.create')
    def test_translate_success(self, mock_create):
        """Test successful translation with OpenAI."""
        # Mock response
        mock_create.return_value = {
            "choices": [{
                "message": {
                    "content": "これはテストです。"
                }
            }]
        }

        config = TranslatorConfig(
            engine="openai",
            openai_model="gpt-3.5-turbo",
            api_key="test-key"
        )
        translator = OpenAITranslator(config)

        result = translator.translate(
            "This is a test.",
            source_lang="en",
            target_lang="ja"
        )

        assert result.translated_text == "これはテストです。"
        assert result.success is True

        # Check API call
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"
        assert call_kwargs["temperature"] == 0.3


class TestTranslatorFactory:
    def test_create_ollama_translator(self):
        """Test creating Ollama translator."""
        config = TranslatorConfig(engine="ollama")
        translator = TranslatorFactory.create(config)

        assert isinstance(translator, OllamaTranslator)

    def test_create_openai_translator(self):
        """Test creating OpenAI translator."""
        config = TranslatorConfig(
            engine="openai",
            api_key="test-key"
        )
        translator = TranslatorFactory.create(config)

        assert isinstance(translator, OpenAITranslator)

    def test_invalid_engine(self):
        """Test invalid engine raises error."""
        config = TranslatorConfig(engine="invalid")

        with pytest.raises(ValueError, match="Unsupported translator engine"):
            TranslatorFactory.create(config)


class TestTranslationResult:
    def test_result_creation(self):
        """Test TranslationResult creation."""
        result = TranslationResult(
            translated_text="これはテストです。",
            source_lang="en",
            target_lang="ja",
            success=True,
            metadata={"model": "gemma3:4b"}
        )

        assert result.translated_text == "これはテストです。"
        assert result.source_lang == "en"
        assert result.target_lang == "ja"
        assert result.success is True
        assert result.metadata["model"] == "gemma3:4b"

    def test_failed_result(self):
        """Test failed translation result."""
        result = TranslationResult(
            translated_text="",
            source_lang="en",
            target_lang="ja",
            success=False,
            error="API connection failed"
        )

        assert result.success is False
        assert result.error == "API connection failed"
        assert result.translated_text == ""
