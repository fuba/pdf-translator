#!/usr/bin/env python3
"""Basic OCR test without PaddleOCR import."""

import logging
from pathlib import Path

from src.extractor import PDFExtractor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test basic PDF extraction."""
    test_file = Path("tests/fixtures/sample_english.pdf")

    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return

    logger.info(f"Testing PDF extraction: {test_file}")

    # Test without OCR first
    extractor = PDFExtractor(use_ocr=False)
    pages = extractor.extract_pdf(test_file)

    logger.info(f"\nExtracted {len(pages)} pages (without OCR)")

    for page in pages[:1]:  # Just first page
        logger.info(f"\nPage {page.page_num + 1}:")
        logger.info(f"  Text blocks: {len(page.text_blocks)}")
        logger.info(f"  Has images: {page.has_images}")

        if page.text_blocks:
            logger.info(f"  Sample text: {page.text_blocks[0].text[:100]}...")

if __name__ == "__main__":
    main()
