#!/usr/bin/env python3
"""Simple OCR test."""

import logging
from pathlib import Path

from src.extractor import PDFExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test basic OCR functionality."""
    # Test with sample PDFs
    test_file = Path("tests/fixtures/sample_mixed_content.pdf")

    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return

    logger.info(f"Testing PDF extraction with OCR support: {test_file}")

    # Create extractor with OCR enabled
    extractor = PDFExtractor(use_ocr=True)

    # Extract pages
    pages = extractor.extract_pdf(test_file)

    logger.info(f"\nExtracted {len(pages)} pages")

    # Show page info
    for page in pages:
        logger.info(f"\nPage {page.page_num + 1}:")
        logger.info(f"  - Text blocks: {len(page.text_blocks)}")
        logger.info(f"  - Has images: {page.has_images}")

        # Check if OCR was used
        ocr_blocks = [b for b in page.text_blocks if b.font_name == "OCR"]
        if ocr_blocks:
            logger.info(f"  - OCR blocks: {len(ocr_blocks)}")

        # Show first few text blocks
        for i, block in enumerate(page.text_blocks[:3]):
            logger.info(f"  - Block {i+1}: {block.text[:50]}...")

    logger.info("\nTest completed!")

if __name__ == "__main__":
    main()
