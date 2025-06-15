#!/usr/bin/env python3
"""Test Japanese text extraction from PDF files."""

from pathlib import Path

from src.extractor import PDFExtractor


def test_pdf_extraction(pdf_path: Path):
    """Test PDF text extraction and display results."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {pdf_path.name}")
    print("=" * 60)

    extractor = PDFExtractor()

    try:
        pages = extractor.extract_pdf(pdf_path)

        for page_num, page in enumerate(pages):
            print(f"\n--- Page {page_num + 1} ---")
            print(f"Dimensions: {page.width:.1f} x {page.height:.1f}")
            print(f"Text blocks: {len(page.text_blocks)}")
            print("\nRaw text preview:")
            print("-" * 40)
            # Show first 500 characters of raw text
            preview = page.raw_text[:500].strip()
            if preview:
                print(preview)
                if len(page.raw_text) > 500:
                    print("... (truncated)")
            else:
                print("(No text content)")
            print("-" * 40)

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Test all sample PDFs."""
    samples_dir = Path("tests/fixtures")

    # Test each PDF file
    pdf_files = list(samples_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in tests/fixtures/")
        return

    print(f"Found {len(pdf_files)} PDF files to test")

    for pdf_file in sorted(pdf_files):
        test_pdf_extraction(pdf_file)


if __name__ == "__main__":
    main()
