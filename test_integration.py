#!/usr/bin/env python3
"""Integration test for PDF translation system."""

from pathlib import Path

from pdf_translator.config.manager import ConfigManager
from pdf_translator.core.pipeline import TranslationPipeline


def test_pdf_translation_pipeline():
    """Test complete PDF translation pipeline."""
    print("=== PDF Translation Pipeline Integration Test ===\n")

    # Setup configuration
    config = ConfigManager()
    pipeline = TranslationPipeline(config)

    # Test file
    input_path = "tests/fixtures/sample_english.pdf"
    output_path = "output/test_translation.html"

    if not Path(input_path).exists():
        print(f"Error: Test PDF not found: {input_path}")
        return

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print("Configuration:")
    print(f"  - Translation engine: {config.get('translation.engine')}")
    print(f"  - Model: {config.get('translation.model')}")
    print(f"  - Target language: {config.get('translation.target_language')}")
    print()

    try:
        # Run the translation pipeline
        result = pipeline.translate(input_path, output_path, pages=[1])

        print("\n=== Translation completed successfully! ===")
        print(f"Processing time: {result['processing_time']:.1f}s")
        print(f"Pages processed: {result['pages_processed']}")
        print(f"Terms extracted: {result['terms_extracted']}")
        print(f"Output saved to: {result['output_path']}")

        # Check output
        output_file = Path(output_path)
        if output_file.exists():
            content = output_file.read_text(encoding="utf-8")
            print("\nOutput preview (first 200 chars):")
            print(content[:200] + "...")

    except Exception as e:
        print("\n=== Translation failed ===")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_pdf_translation_pipeline()
