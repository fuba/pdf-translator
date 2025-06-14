"""Demo script to test term mining functionality."""
import logging
from pathlib import Path

import yaml

from src.extractor import PDFExtractor
from src.term_miner import TermMiner, TermMinerConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_spacy_availability():
    """Test if spaCy models are available."""
    print("\n=== Testing spaCy Availability ===")

    try:
        import spacy
        print("✓ spaCy is available")

        # Test English model
        try:
            spacy.load("en_core_web_sm")
            print("✓ English model (en_core_web_sm) is available")
        except Exception as e:
            print(f"✗ English model not available: {e}")
            print("  Run: python -m spacy download en_core_web_sm")
            return False

        # Test Japanese model (optional)
        try:
            spacy.load("ja_core_news_sm")
            print("✓ Japanese model (ja_core_news_sm) is available")
        except Exception as e:
            print(f"⚠️  Japanese model not available: {e}")
            print("  Run: python -m spacy download ja_core_news_sm")

        return True

    except ImportError:
        print("✗ spaCy is not installed")
        return False


def test_term_extraction_simple():
    """Test simple term extraction."""
    print("\n=== Testing Simple Term Extraction ===")

    config = TermMinerConfig(
        min_frequency=1,
        max_terms=20,
        wikipedia_lookup=False  # Disable for speed
    )
    miner = TermMiner(config)

    text = """
    Machine learning is a subset of artificial intelligence (AI) that provides
    systems the ability to automatically learn and improve from experience without
    being explicitly programmed. Deep learning is a subset of machine learning.

    Neural networks, particularly Convolutional Neural Networks (CNNs) and
    Recurrent Neural Networks (RNNs), are commonly used in deep learning applications.
    Natural Language Processing (NLP) is another important field in AI.
    """

    result = miner.extract_terms(text)

    if result.success:
        print(f"✓ Extracted {len(result.terms)} terms")
        print(f"  Total terms found: {result.total_terms_found}")
        print(f"  After filtering: {result.filtered_terms}")
        print(f"  Method: {result.metadata.get('method', 'unknown')}")

        print("\nExtracted terms:")
        for i, term in enumerate(result.terms[:10], 1):  # Show first 10
            print(f"  {i}. {term.text} (freq: {term.frequency}, conf: {term.confidence:.2f})")
            if term.context:
                context_preview = term.context[:60] + "..." if len(term.context) > 60 else term.context
                print(f"      Context: {context_preview}")
    else:
        print(f"✗ Term extraction failed: {result.error}")
        return False

    return True


def test_term_extraction_with_pdf():
    """Test term extraction with actual PDF content."""
    print("\n=== Testing Term Extraction with PDF ===")

    pdf_path = Path("tests/fixtures/sample_english.pdf")
    if not pdf_path.exists():
        print(f"⚠️  Test PDF not found: {pdf_path}")
        return True  # Not critical

    # Extract text from PDF
    extractor = PDFExtractor()
    pages = extractor.extract_pdf(pdf_path)

    if not pages:
        print("✗ No pages extracted from PDF")
        return False

    # Combine text from all pages
    full_text = " ".join(page.raw_text for page in pages)
    print(f"✓ Extracted {len(full_text)} characters from PDF")

    # Extract terms
    config = TermMinerConfig(
        min_frequency=1,
        max_terms=15,
        wikipedia_lookup=False
    )
    miner = TermMiner(config)

    result = miner.extract_terms(full_text)

    if result.success:
        print(f"✓ Extracted {len(result.terms)} terms from PDF")

        print("\nTop terms from PDF:")
        for i, term in enumerate(result.terms[:8], 1):
            print(f"  {i}. {term.text} (freq: {term.frequency})")
    else:
        print(f"✗ Term extraction failed: {result.error}")
        return False

    return True


def test_wikipedia_lookup():
    """Test Wikipedia translation lookup."""
    print("\n=== Testing Wikipedia Translation Lookup ===")

    config = TermMinerConfig(
        min_frequency=1,
        max_terms=5,
        wikipedia_lookup=True
    )
    miner = TermMiner(config)

    # Simple text with known technical terms
    text = """
    Machine learning and artificial intelligence are transformative technologies.
    Deep learning and neural networks enable many AI applications.
    """

    print("Extracting terms with Wikipedia translation lookup...")
    result = miner.extract_terms(text)

    if result.success:
        print(f"✓ Extracted {len(result.terms)} terms")

        print("\nTerms with translations:")
        for term in result.terms:
            translations = ", ".join(f"{lang}: {trans}" for lang, trans in term.translations.items())
            if translations:
                print(f"  {term.text} → {translations}")
            else:
                print(f"  {term.text} (no translation found)")
    else:
        print(f"✗ Term extraction with Wikipedia lookup failed: {result.error}")
        return False

    return True


def test_config_from_file():
    """Test loading configuration from config file."""
    print("\n=== Testing Configuration Loading ===")

    config_path = Path("config/config.yml")
    if not config_path.exists():
        print(f"⚠️  Config file not found: {config_path}")
        return True

    with open(config_path, 'r') as f:
        full_config = yaml.safe_load(f)

    term_config_dict = full_config.get("term_extraction", {})
    config = TermMinerConfig.from_dict(term_config_dict)

    print("✓ Loaded configuration:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Min frequency: {config.min_frequency}")
    print(f"  Max terms: {config.max_terms}")
    print(f"  Wikipedia lookup: {config.wikipedia_lookup}")

    return True


def main():
    """Run all term mining tests."""
    print("PDF Translation System - Term Mining Demo")
    print("=" * 50)

    tests = [
        ("spaCy Availability", test_spacy_availability),
        ("Simple Term Extraction", test_term_extraction_simple),
        ("PDF Term Extraction", test_term_extraction_with_pdf),
        ("Configuration Loading", test_config_from_file),
        ("Wikipedia Lookup", test_wikipedia_lookup),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"\n✓ {test_name} passed!")
            else:
                print(f"\n✗ {test_name} failed!")
        except Exception as e:
            print(f"\n✗ {test_name} error: {str(e)}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {status}: {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All term mining tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()
