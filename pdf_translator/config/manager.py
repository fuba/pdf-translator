"""
Configuration Manager - Handle application configuration.

This module provides a unified interface for managing configuration settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class ConfigManager:
    """Manage application configuration."""
    
    def __init__(self, config_path: str = "config/config.yml"):
        """Initialize configuration manager."""
        # Load environment variables from .env file if it exists
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Check for API keys in environment
        if openai_key := os.getenv("OPENAI_API_KEY"):
            self.set("translation.openai.api_key", openai_key)
            self.set("translator.api_key", openai_key)  # Legacy support
        
        # Check for Ollama URL override
        if ollama_url := os.getenv("OLLAMA_API_URL"):
            self.set("translation.ollama.api_url", ollama_url)
            self.set("translator.base_url", ollama_url)  # Legacy support
        
        # Check for Ollama model override
        if ollama_model := os.getenv("OLLAMA_MODEL"):
            self.set("translation.ollama.model", ollama_model)
            self.set("translator.model", ollama_model)  # Legacy support
        
        # Check for Ollama timeout override
        if ollama_timeout := os.getenv("OLLAMA_TIMEOUT"):
            try:
                timeout_val = float(ollama_timeout)
                self.set("translation.ollama.timeout", timeout_val)
                self.set("translator.timeout", timeout_val)  # Legacy support
            except ValueError:
                pass  # Ignore invalid timeout values
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        # Handle legacy key mappings
        legacy_mappings = {
            "translation.engine": "translator.engine",
            "translation.source_language": "source_language",
            "translation.target_language": "target_language",
            "translation.ollama.model": "translator.model",
            "translation.ollama.api_url": "translator.base_url",
            "translation.openai.model": "translator.openai_model",
            "translation.openai.api_key": "translator.api_key",
            "extraction.max_pages": "max_pages",
            "extraction.enable_ocr": "use_ocr",
            "layout.enabled": "layout_analysis",
            "term_extraction.enabled": "term_extraction.enabled",
            "output.format": "output_format"
        }
        
        # Use legacy mapping if available
        mapped_key = legacy_mappings.get(key, key)
        keys = mapped_key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-notation key."""
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def get_dict(self, prefix: str) -> Dict[str, Any]:
        """Get configuration section as dictionary."""
        value = self.get(prefix, {})
        return value if isinstance(value, dict) else {}
    
    def save(self, path: Optional[str] = None) -> None:
        """Save current configuration to file."""
        save_path = Path(path) if path else self.config_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
    
    def get_translator_config(self):
        """Get translator configuration."""
        from pdf_translator.translator import TranslatorConfig
        
        translator_config = self.get_dict("translator")
        return TranslatorConfig.from_dict(translator_config)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ConfigManager(path='{self.config_path}')"