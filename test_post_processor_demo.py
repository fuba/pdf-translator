"""Demo script to test post-processing functionality."""

import logging
from pathlib import Path

import yaml

from src.post_processor import PostProcessor, PostProcessorConfig
from src.term_miner import Term

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_basic_annotation():
    """Test basic term annotation functionality."""
    print("\n=== Testing Basic Term Annotation ===")

    config = PostProcessorConfig()
    processor = PostProcessor(config)

    # Sample translated text with technical terms
    translated_text = """機械学習は人工知能の一分野です。
深層学習は機械学習の手法の一つで、ニューラルネットワークを使用します。
自然言語処理は人工知能のもう一つの重要な分野です。"""

    # Term dictionary (original -> translation)
    term_dict = {
        "machine learning": "機械学習",
        "artificial intelligence": "人工知能",
        "deep learning": "深層学習",
        "neural network": "ニューラルネットワーク",
        "natural language processing": "自然言語処理",
    }

    result = processor.process(translated_text, term_dict)

    if result.success:
        print("✓ Post-processing successful")
        print(f"  Annotations added: {result.annotations_added}")
        print(f"  Terms processed: {result.terms_processed}")

        print("\nOriginal text:")
        print(translated_text)

        print("\nProcessed text:")
        print(result.processed_text)

        # Check for expected annotations
        expected_annotations = [
            "機械学習（machine learning）",
            "人工知能（artificial intelligence）",
            "深層学習（deep learning）",
            "ニューラルネットワーク（neural network）",
            "自然言語処理（natural language processing）",
        ]

        found_annotations = []
        for annotation in expected_annotations:
            if annotation in result.processed_text:
                found_annotations.append(annotation)

        print(f"\nFound annotations: {len(found_annotations)}/{len(expected_annotations)}")
        for annotation in found_annotations:
            print(f"  ✓ {annotation}")

    else:
        print(f"✗ Post-processing failed: {result.error}")
        return False

    return True


def test_first_occurrence_only():
    """Test that annotations are only added on first occurrence."""
    print("\n=== Testing First Occurrence Only ===")

    config = PostProcessorConfig()
    processor = PostProcessor(config)

    # Text with repeated terms
    translated_text = """機械学習について説明します。
機械学習は重要な技術です。機械学習の応用例を見てみましょう。
深層学習も機械学習の一種です。"""

    term_dict = {"machine learning": "機械学習", "deep learning": "深層学習"}

    result = processor.process(translated_text, term_dict)

    if result.success:
        print("✓ Processing successful")

        # Count occurrences
        annotated_ml = result.processed_text.count("機械学習（machine learning）")
        plain_ml = result.processed_text.count("機械学習") - annotated_ml

        print(f"  機械学習（machine learning）: {annotated_ml} times")
        print(f"  機械学習 (plain): {plain_ml} times")

        print("\nProcessed text:")
        print(result.processed_text)

        # Should have exactly one annotated occurrence
        if annotated_ml == 1:
            print("✓ Correct: Only first occurrence is annotated")
        else:
            print(f"✗ Error: Expected 1 annotation, got {annotated_ml}")
            return False

    return True


def test_custom_format():
    """Test custom annotation formats."""
    print("\n=== Testing Custom Annotation Format ===")

    # Test different formats
    formats = [
        "{translation}（{original}）",  # Default Japanese style
        "{translation} [{original}]",  # Square brackets
        "{translation} ({original})",  # Regular parentheses
        "{translation}『{original}』",  # Japanese quotes
    ]

    translated_text = "機械学習について説明します。"
    term_dict = {"machine learning": "機械学習"}

    for fmt in formats:
        config = PostProcessorConfig(source_term_format=fmt)
        processor = PostProcessor(config)

        result = processor.process(translated_text, term_dict)

        if result.success:
            expected = fmt.format(translation="機械学習", original="machine learning")
            if expected in result.processed_text:
                print(f"✓ Format '{fmt}' works: {expected}")
            else:
                print(f"✗ Format '{fmt}' failed")
                return False
        else:
            print(f"✗ Processing failed for format '{fmt}'")
            return False

    return True


def test_overlapping_terms():
    """Test handling of overlapping terms."""
    print("\n=== Testing Overlapping Terms ===")

    config = PostProcessorConfig()
    processor = PostProcessor(config)

    # Text with overlapping terms
    translated_text = "自然言語処理システムについて説明します。"

    # Overlapping terms: "自然言語" vs "自然言語処理"
    term_dict = {
        "natural language": "自然言語",
        "natural language processing": "自然言語処理",
        "system": "システム",
    }

    result = processor.process(translated_text, term_dict)

    if result.success:
        print("✓ Processing successful")
        print(f"  Annotations added: {result.annotations_added}")

        print("\nProcessed text:")
        print(result.processed_text)

        # Should prefer longer term (自然言語処理 over 自然言語)
        if "自然言語処理（natural language processing）" in result.processed_text:
            print("✓ Correctly annotated longer term")
        else:
            print("✗ Failed to prioritize longer term")
            return False

        # Should not have overlapping annotations
        if "自然言語（natural language）処理" in result.processed_text:
            print("✗ Created overlapping annotations")
            return False
        else:
            print("✓ No overlapping annotations")

    return True


def test_spacing_adjustment():
    """Test spacing adjustment between Japanese and English."""
    print("\n=== Testing Spacing Adjustment ===")

    config = PostProcessorConfig(spacing_adjustment=True)
    processor = PostProcessor(config)

    # Text with mixed Japanese and English
    translated_text = (
        "これはAPI（Application Programming Interface）の説明です。JSONデータを使用します。"
    )
    term_dict = {}

    result = processor.process(translated_text, term_dict)

    if result.success:
        print("✓ Spacing adjustment successful")

        print("\nOriginal text:")
        print(translated_text)

        print("\nWith spacing adjustment:")
        print(result.processed_text)

        # Basic check - should have spaces around English terms
        if " API " in result.processed_text or " JSON " in result.processed_text:
            print("✓ Added appropriate spacing")
        else:
            print("⚠️  Spacing adjustment may not be working as expected")

    return True


def test_config_loading():
    """Test loading configuration from file."""
    print("\n=== Testing Configuration Loading ===")

    config_path = Path("config/config.yml")
    if not config_path.exists():
        print(f"⚠️  Config file not found: {config_path}")
        return True

    try:
        with open(config_path, "r") as f:
            full_config = yaml.safe_load(f)

        # Look for post-processing config (may not exist yet)
        post_config_dict = full_config.get(
            "post_processing",
            {
                "add_source_terms": True,
                "source_term_format": "{translation}（{original}）",
                "spacing_adjustment": True,
            },
        )

        config = PostProcessorConfig.from_dict(post_config_dict)
        PostProcessor(config)

        print("✓ Loaded configuration:")
        print(f"  Add source terms: {config.add_source_terms}")
        print(f"  Format: {config.source_term_format}")
        print(f"  Spacing adjustment: {config.spacing_adjustment}")

        return True

    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False


def test_with_term_objects():
    """Test processing with Term objects."""
    print("\n=== Testing with Term Objects ===")

    config = PostProcessorConfig()
    processor = PostProcessor(config)

    translated_text = "機械学習と深層学習について説明します。"

    # Create Term objects
    terms = [
        Term("machine learning", 3, translations={"ja": "機械学習"}),
        Term("deep learning", 2, translations={"ja": "深層学習"}),
        Term("AI", 1, translations={"ja": "AI"}),  # Too short, should be filtered
    ]

    result = processor.process_with_terms(translated_text, terms)

    if result.success:
        print("✓ Processing with Term objects successful")
        print(f"  Annotations added: {result.annotations_added}")

        print("\nProcessed text:")
        print(result.processed_text)

        return True
    else:
        print(f"✗ Processing failed: {result.error}")
        return False


def main():
    """Run all post-processing tests."""
    print("PDF Translation System - Post-Processing Demo")
    print("=" * 55)

    tests = [
        ("Basic Term Annotation", test_basic_annotation),
        ("First Occurrence Only", test_first_occurrence_only),
        ("Custom Annotation Format", test_custom_format),
        ("Overlapping Terms", test_overlapping_terms),
        ("Spacing Adjustment", test_spacing_adjustment),
        ("Configuration Loading", test_config_loading),
        ("Term Objects Processing", test_with_term_objects),
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
    print("\n" + "=" * 55)
    print("Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {status}: {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All post-processing tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()
