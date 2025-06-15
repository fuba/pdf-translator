#!/usr/bin/env python3
"""Simple pipeline test to identify bottlenecks."""

import logging

from pdf_translator.config.manager import ConfigManager
from pdf_translator.core.pipeline import TranslationPipeline

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_analysis_only():
    """Test only PDF analysis."""
    print("=== Testing PDF Analysis Only ===")
    config = ConfigManager()
    pipeline = TranslationPipeline(config)

    try:
        result = pipeline.analyze("tests/fixtures/sample_english.pdf", pages=[1])
        print(f"Analysis successful: {result}")
        return True
    except Exception as e:
        print(f"Analysis failed: {e}")
        return False


def test_extractor_only():
    """Test only PDF extraction."""
    print("=== Testing PDF Extraction Only ===")
    from pdf_translator.extractor import PDFExtractor

    config = ConfigManager()
    extractor = PDFExtractor(config)

    try:
        document = extractor.extract("tests/fixtures/sample_english.pdf", pages=[1])
        print(f"Extraction successful: {document}")
        print(f"First page text: {document.pages[0].text_content[:100]}...")
        return True
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def test_translator_only():
    """Test only translation."""
    print("=== Testing Translation Only ===")
    from pdf_translator.translator import OllamaTranslator

    config = ConfigManager()
    translator = OllamaTranslator(config)

    try:
        result = translator.translate("This is a test.")
        print(f"Translation successful: {result}")
        return True
    except Exception as e:
        print(f"Translation failed: {e}")
        return False


def test_renderer_only():
    """Test only rendering."""
    print("=== Testing Rendering Only ===")
    from pathlib import Path

    from pdf_translator.extractor import PageInfo
    from pdf_translator.renderer import DocumentRenderer

    config = ConfigManager()
    renderer = DocumentRenderer(config)

    # Create simple test page
    page_info = PageInfo(
        page_num=0,
        width=595,
        height=842,
        text_blocks=[],
        raw_text="This is a test.",
        has_images=False,
    )
    translated_texts = {0: "これはテストです。"}

    try:
        output_path = Path("test_render_output.html")
        renderer.render_from_pages([page_info], translated_texts, output_path)
        print("Rendering successful")
        return True
    except Exception as e:
        print(f"Rendering failed: {e}")
        return False


if __name__ == "__main__":
    print("Starting component tests...\n")

    # Test individual components
    extractor_ok = test_extractor_only()
    print()

    translator_ok = test_translator_only()
    print()

    renderer_ok = test_renderer_only()
    print()

    # Test analysis pipeline if components work
    if extractor_ok:
        analysis_ok = test_analysis_only()
        print()

    print("=== Test Summary ===")
    print(f"Extractor: {'✓' if extractor_ok else '✗'}")
    print(f"Translator: {'✓' if translator_ok else '✗'}")
    print(f"Renderer: {'✓' if renderer_ok else '✗'}")
    if extractor_ok:
        print(f"Analysis: {'✓' if analysis_ok else '✗'}")
