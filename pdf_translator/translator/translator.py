"""Translation module using Ollama and OpenAI APIs."""
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from pdf_translator.config.manager import ConfigManager

# OpenAI import is optional
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)


@dataclass
class TranslatorConfig:
    """Configuration for translator."""

    engine: str = "ollama"  # ollama or openai
    model: str = "gemma3:12b"  # Model name for Ollama
    openai_model: str = "gpt-3.5-turbo"  # Model name for OpenAI
    api_key: Optional[str] = None  # API key for OpenAI
    base_url: str = "http://localhost:11434/api"  # Ollama API endpoint
    temperature: float = 0.3  # Lower for more consistent translations
    max_tokens: int = 4096  # Maximum tokens per request
    timeout: int = 300  # Request timeout in seconds

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TranslatorConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    translated_text: str
    source_lang: str
    target_lang: str
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTranslator(ABC):
    """Base class for translators."""

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        # Create translator config from ConfigManager
        self.translator_config = TranslatorConfig(
            engine=self.config.get("translator.engine", "ollama"),
            model=self.config.get("translator.model", "gemma3:12b"),
            base_url=self.config.get("translator.base_url", "http://localhost:11434/api"),
            api_key=self.config.get("translator.api_key", ""),
            temperature=self.config.get("translator.temperature", 0.3),
            max_tokens=self.config.get("translator.max_tokens", 4096),
            timeout=self.config.get("translator.timeout", 120.0)
        )

    def get_system_prompt(self, source_lang: str, target_lang: str,
                         preserve_format: bool = True) -> str:
        """Generate system prompt for translation."""
        lang_names = {
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "auto": "auto-detected language"
        }

        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)

        prompt = f"""You are a professional translator specializing in technical documents.
Translate the following text from {source_name} to {target_name}.

Important guidelines:
1. Preserve the original layout and formatting
2. Maintain paragraph breaks and structure
3. For technical terms, provide the translation followed by the original term
   in parentheses on first occurrence
4. Do not translate code blocks, formulas, or figure/table captions
5. Ensure accuracy while maintaining natural flow in the target language
6. Keep URLs, file paths, and technical identifiers unchanged

Output only the translated text without any explanations or metadata."""

        return prompt

    def prepare_text(self, text: str) -> str:
        """Prepare text for translation."""
        # Basic preprocessing - can be extended
        return text.strip()

    @abstractmethod
    def translate(self, text: str, source_lang: str = "auto",
                 target_lang: str = "ja") -> TranslationResult:
        """Translate text."""
        pass

    def translate_batch(self, texts: List[str], source_lang: str = "auto",
                       target_lang: str = "ja") -> List[TranslationResult]:
        """Translate multiple texts."""
        results = []
        for text in texts:
            result = self.translate(text, source_lang, target_lang)
            results.append(result)
        return results


class OllamaTranslator(BaseTranslator):
    """Translator using Ollama API."""

    def __init__(self, config: Optional[ConfigManager] = None):
        super().__init__(config)

    def translate(self, text: str, source_lang: str = "auto",
                 target_lang: str = "ja") -> TranslationResult:
        """Translate text using Ollama."""
        try:
            logger.info(f"Starting translation with Ollama (text length: {len(text)})")
            # Prepare request
            system_prompt = self.get_system_prompt(source_lang, target_lang)
            prepared_text = self.prepare_text(text)

            # Build payload
            payload = {
                "model": self.translator_config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prepared_text}
                ],
                "stream": False,
                "options": {
                    "temperature": self.translator_config.temperature,
                    "num_predict": self.translator_config.max_tokens
                }
            }

            # Make request
            url = f"{self.translator_config.base_url}/chat"
            logger.info(f"Sending request to {url} with model {self.translator_config.model}")
            logger.debug(f"Request payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.translator_config.timeout
            )
            logger.info(f"Received response status: {response.status_code}")
            response.raise_for_status()

            # Parse response
            result_data = response.json()
            translated_text = result_data["message"]["content"]

            return TranslationResult(
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                success=True,
                metadata={
                    "model": self.translator_config.model,
                    "engine": "ollama"
                }
            )

        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                success=False,
                error=str(e)
            )

    def check_connection(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            response = requests.get(
                f"{self.translator_config.base_url}/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available models."""
        try:
            response = requests.get(
                f"{self.translator_config.base_url}/tags",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception:
            return []


class OpenAITranslator(BaseTranslator):
    """Translator using OpenAI API."""

    def __init__(self, config: Optional[ConfigManager] = None):
        super().__init__(config)
        if not HAS_OPENAI:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        if not self.translator_config.api_key:
            raise ValueError("OpenAI API key is required")
        openai.api_key = self.translator_config.api_key

    def translate(self, text: str, source_lang: str = "auto",
                 target_lang: str = "ja") -> TranslationResult:
        """Translate text using OpenAI."""
        try:
            # Prepare request
            system_prompt = self.get_system_prompt(source_lang, target_lang)
            prepared_text = self.prepare_text(text)

            # Make request
            response = openai.ChatCompletion.create(
                model=self.translator_config.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prepared_text}
                ],
                temperature=self.translator_config.temperature,
                max_tokens=self.translator_config.max_tokens
            )

            # Extract translated text
            translated_text = response["choices"][0]["message"]["content"]

            return TranslationResult(
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                success=True,
                metadata={
                    "model": self.translator_config.openai_model,
                    "engine": "openai",
                    "usage": response.get("usage", {})
                }
            )

        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                success=False,
                error=str(e)
            )


class TranslatorFactory:
    """Factory for creating translator instances."""

    @staticmethod
    def create(config: TranslatorConfig) -> BaseTranslator:
        """Create translator based on config."""
        if config.engine == "ollama":
            return OllamaTranslator(config)
        elif config.engine == "openai":
            return OpenAITranslator(config)
        else:
            raise ValueError(f"Unsupported translator engine: {config.engine}")

    @staticmethod
    def from_config_file(config_path: Path) -> BaseTranslator:
        """Create translator from config file."""
        import yaml

        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)

        translator_config = full_config.get("translator", {})
        config = TranslatorConfig.from_dict(translator_config)

        # Check for API key in environment
        if config.engine == "openai" and not config.api_key:
            config.api_key = os.getenv("OPENAI_API_KEY")

        return TranslatorFactory.create(config)
