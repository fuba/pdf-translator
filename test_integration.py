"""Integration test for PDF translation system"""
from pathlib import Path

import yaml

from src.extractor import PDFExtractor
from src.translator import TranslatorConfig, TranslatorFactory


def test_pdf_translation_pipeline():
    """Test PDF extraction and translation pipeline"""
    print("=== PDF Translation Pipeline Test ===\n")

    # 1. Extract text from PDF
    pdf_path = Path("tests/fixtures/sample_english.pdf")
    if not pdf_path.exists():
        print(f"Error: Test PDF not found: {pdf_path}")
        return

    print(f"1. Extracting text from: {pdf_path.name}")
    extractor = PDFExtractor()
    pdf_data = extractor.extract_pdf(pdf_path)

    print(f"   - Pages extracted: {len(pdf_data)}")
    print(f"   - Total text blocks: {sum(len(p.text_blocks) for p in pdf_data)}")

    # Show first page content
    if pdf_data:
        first_page_text = pdf_data[0].raw_text[:200]
        print(f"   - First page preview: {first_page_text}...")

    # 2. Translate the content
    print("\n2. Setting up translator")
    config_path = Path("config/config.yml")
    with open(config_path, 'r') as f:
        full_config = yaml.safe_load(f)

    translator_config = full_config.get("translator", {})
    config = TranslatorConfig.from_dict(translator_config)
    translator = TranslatorFactory.create(config)

    print(f"   - Engine: {config.engine}")
    print(f"   - Model: {config.model}")

    # 3. Translate first page
    print("\n3. Translating first page")
    if pdf_data:
        page_text = pdf_data[0].raw_text
        print(f"   - Original text length: {len(page_text)} characters")

        result = translator.translate(
            page_text,
            source_lang="en",
            target_lang="ja"
        )

        if result.success:
            print("   - Translation successful!")
            print(f"   - Translated text length: {len(result.translated_text)} characters")
            print(f"\n   Original (first 150 chars):\n   {page_text[:150]}...")
            print(f"\n   Translated (first 150 chars):\n   {result.translated_text[:150]}...")
        else:
            print(f"   - Translation failed: {result.error}")

    # 4. Test with custom prompt for better results
    print("\n4. Testing with improved system prompt")

    # Create a custom translator with better prompt
    class ImprovedOllamaTranslator(translator.__class__):
        def get_system_prompt(self, source_lang: str, target_lang: str,
                             preserve_format: bool = True) -> str:
            return """You are a professional translator. Translate the given text from English to Japanese.
Keep the translation natural and accurate. 
IMPORTANT: Only output the translated text, nothing else.
Do not add any explanations or metadata."""

    improved_translator = ImprovedOllamaTranslator(config)

    test_text = "This is a sample PDF document for testing."
    result = improved_translator.translate(test_text, "en", "ja")

    if result.success:
        print(f"   Original: {test_text}")
        print(f"   Translated: {result.translated_text}")

    print("\n=== Test completed ===")


if __name__ == "__main__":
    test_pdf_translation_pipeline()
