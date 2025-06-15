#!/usr/bin/env python3
"""Test script to verify development environment setup."""

import sys
from pathlib import Path


def test_imports():
    """Test that all major dependencies can be imported."""
    print("Testing imports...")

    modules = {
        "PyMuPDF": "fitz",
        "PaddleOCR": "paddleocr",
        "spaCy": "spacy",
        "Ollama": "ollama",
        "OpenAI": "openai",
        "Transformers": "transformers",
        "PyYAML": "yaml",
        "Jinja2": "jinja2",
        "Rich": "rich",
    }

    failed = []
    for name, module in modules.items():
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError as e:
            print(f"✗ {name}: {e}")
            failed.append(name)

    return len(failed) == 0


def test_ollama_connection():
    """Test connection to Ollama server."""
    print("\nTesting Ollama connection...")
    try:
        import requests
        import os
        from pdf_translator.config.manager import ConfigManager

        # Load configuration to get expected model
        try:
            config = ConfigManager()
            expected_model = os.getenv("OLLAMA_MODEL") or config.get("translator.model", "gemma3:12b-it-q8_0")
            api_url = os.getenv("OLLAMA_API_URL") or config.get("translator.base_url", "http://localhost:11434/api")
        except:
            expected_model = "gemma3:12b-it-q8_0"
            api_url = "http://localhost:11434/api"

        # Use requests directly for better compatibility
        response = requests.get(f"{api_url.replace('/api', '')}/api/tags")
        response.raise_for_status()
        data = response.json()

        print("✓ Connected to Ollama")
        print(f"  Available models: {len(data['models'])}")

        # Check for expected model
        model_names = [m["name"] for m in data["models"]]
        print(f"  Models: {model_names}")

        if expected_model in model_names:
            print(f"✓ {expected_model} is available")
            return True
        else:
            print(f"✗ {expected_model} not found")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ Ollama server not running")
        print("  Run 'ollama serve' to start the server")
        return False
    except Exception as e:
        print(f"✗ Ollama connection failed: {e}")
        return False


def test_spacy_model():
    """Test spaCy Japanese model."""
    print("\nTesting spaCy Japanese model...")
    try:
        import spacy

        nlp = spacy.load("ja_core_news_sm")
        doc = nlp("これはテストです。")
        print("✓ spaCy Japanese model loaded")
        print(f"  Tokens: {[token.text for token in doc]}")
        return True
    except Exception as e:
        print(f"✗ spaCy model loading failed: {e}")
        return False


def test_project_structure():
    """Test project directory structure."""
    print("\nTesting project structure...")

    dirs = [
        "src",
        "src/extractor",
        "src/layout_analyzer",
        "src/term_miner",
        "src/translator",
        "src/post_processor",
        "src/renderer",
        "tests",
        "config",
        "logs",
        "output",
        "cache",
    ]

    missing = []
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✓ {dir_name}/")
        else:
            print(f"✗ {dir_name}/ (missing)")
            missing.append(dir_name)

    return len(missing) == 0


def main():
    print("PDF Translator - Environment Setup Test")
    print("=" * 40)

    tests = [
        test_imports,
        test_ollama_connection,
        test_spacy_model,
        test_project_structure,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed! Environment is ready.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
