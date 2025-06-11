"""Demo script to test translator functionality"""
import logging
from pathlib import Path
import yaml

from src.translator import TranslatorFactory, TranslatorConfig, OllamaTranslator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_ollama_connection():
    """Test Ollama server connection"""
    print("\n=== Testing Ollama Connection ===")
    config = TranslatorConfig(engine="ollama")
    translator = OllamaTranslator(config)
    
    if translator.check_connection():
        print("✓ Ollama server is running")
        
        models = translator.list_models()
        print(f"✓ Available models: {models}")
        
        if "gemma3:12b" in models:
            print("✓ gemma3:12b model is available")
        else:
            print("✗ gemma3:12b model not found. Please run: ollama pull gemma3:12b")
            return False
    else:
        print("✗ Ollama server is not running. Please run: ollama serve")
        return False
    
    return True


def test_translation():
    """Test actual translation"""
    print("\n=== Testing Translation ===")
    
    # Load config
    config_path = Path("config/config.yml")
    with open(config_path, 'r') as f:
        full_config = yaml.safe_load(f)
    
    translator_config = full_config.get("translator", {})
    config = TranslatorConfig.from_dict(translator_config)
    
    # Create translator
    translator = TranslatorFactory.create(config)
    
    # Test texts
    test_texts = [
        "Hello, world!",
        # "This is a test of the PDF translation system.",
        # "Technical terms like machine learning (ML) should be preserved.",
        # "Multiple paragraphs.\n\nShould maintain structure."
    ]
    
    print(f"\nUsing {config.engine} with model {config.model}")
    print("-" * 50)
    
    for text in test_texts:
        print(f"\nOriginal: {text}")
        result = translator.translate(text, source_lang="en", target_lang="ja")
        
        if result.success:
            print(f"Translated: {result.translated_text}")
        else:
            print(f"Error: {result.error}")
            return False
    
    return True


def test_batch_translation():
    """Test batch translation"""
    print("\n=== Testing Batch Translation ===")
    
    config = TranslatorConfig(engine="ollama")
    translator = OllamaTranslator(config)
    
    texts = [
        "First sentence.",
        "Second sentence.",
        "Third sentence with technical terms like API."
    ]
    
    results = translator.translate_batch(texts, source_lang="en", target_lang="ja")
    
    for i, (text, result) in enumerate(zip(texts, results)):
        print(f"\n{i+1}. Original: {text}")
        if result.success:
            print(f"   Translated: {result.translated_text}")
        else:
            print(f"   Error: {result.error}")
    
    return all(r.success for r in results)


def main():
    """Run all tests"""
    print("PDF Translation System - Translator Module Demo")
    print("=" * 50)
    
    # Check Ollama connection first
    if not test_ollama_connection():
        print("\n⚠️  Please ensure Ollama is running and gemma3:12b model is available")
        print("Run the following commands:")
        print("  make run-ollama  # or: ollama serve")
        print("  ollama pull gemma3:12b")
        return
    
    # Test translation
    if test_translation():
        print("\n✓ Translation test passed!")
    else:
        print("\n✗ Translation test failed!")
        return
    
    # Test batch translation
    if test_batch_translation():
        print("\n✓ Batch translation test passed!")
    else:
        print("\n✗ Batch translation test failed!")
    
    print("\n" + "=" * 50)
    print("All tests completed successfully! 🎉")


if __name__ == "__main__":
    main()