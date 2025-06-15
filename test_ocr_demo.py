#!/usr/bin/env python3
"""Demo script to test OCR functionality."""

import logging
from pathlib import Path

from src.extractor import OCRConfig, OCRExtractor, PDFExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ocr_extraction():
    """Test OCR extraction with a sample PDF."""
    # Create OCR extractor with Japanese support
    ocr_config = OCRConfig(
        lang="japan",  # Use Japanese OCR model
        use_angle_cls=True,
        drop_score=0.3,  # Lower threshold for demo
    )
    OCRExtractor(ocr_config)

    # Test with sample PDFs
    test_files = [
        Path("tests/fixtures/sample_japanese.pdf"),
        Path("tests/fixtures/sample_mixed_content.pdf"),
    ]

    for pdf_path in test_files:
        if not pdf_path.exists():
            logger.warning(f"Test file not found: {pdf_path}")
            continue

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing OCR extraction with: {pdf_path.name}")
        logger.info(f"{'=' * 60}")

        try:
            # Extract with standard PDF extractor (with OCR fallback)
            extractor = PDFExtractor(use_ocr=True)
            pages = extractor.extract_pdf(pdf_path)

            logger.info(f"Extracted {len(pages)} pages")

            for page in pages[:2]:  # Show first 2 pages
                logger.info(f"\nPage {page.page_num + 1}:")
                logger.info(f"  - Dimensions: {page.width:.1f} x {page.height:.1f}")
                logger.info(f"  - Has images: {page.has_images}")
                logger.info(f"  - Text blocks: {len(page.text_blocks)}")

                if page.text_blocks:
                    logger.info("  - Sample text blocks:")
                    for i, block in enumerate(page.text_blocks[:3]):
                        logger.info(
                            f"    Block {i + 1} ({block.block_type}, size={block.font_size:.1f}):"
                        )
                        logger.info(
                            f"      Text: {block.text[:100]}{'...' if len(block.text) > 100 else ''}"
                        )

                # Check if OCR was used
                if any(block.font_name == "OCR" for block in page.text_blocks):
                    logger.info("  - OCR was used for this page")

        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            import traceback

            traceback.print_exc()


def test_image_pdf_creation_and_ocr():
    """Create an image-based PDF and test OCR extraction."""
    logger.info(f"\n{'=' * 60}")
    logger.info("Creating and testing image-based PDF")
    logger.info(f"{'=' * 60}")

    try:
        import tempfile

        import fitz
        from PIL import Image, ImageDraw, ImageFont

        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create an image with text
            img = Image.new("RGB", (800, 600), color="white")
            draw = ImageDraw.Draw(img)

            # Try to use a font, fallback to default
            try:
                font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
                font_normal = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                font_large = ImageFont.load_default()
                font_normal = ImageFont.load_default()

            # Draw text
            draw.text((50, 50), "PDF OCR Demo", fill="black", font=font_large)
            draw.text(
                (50, 150),
                "This is a test of the OCR functionality.",
                fill="black",
                font=font_normal,
            )
            draw.text(
                (50, 200),
                "The text in this PDF is actually an image.",
                fill="black",
                font=font_normal,
            )
            draw.text(
                (50, 250),
                "PaddleOCR should extract this text correctly.",
                fill="black",
                font=font_normal,
            )

            # Save image
            img_path = tmpdir_path / "test_page.png"
            img.save(img_path)

            # Create PDF with the image
            pdf_path = tmpdir_path / "image_based.pdf"
            doc = fitz.open()
            page = doc.new_page(width=800, height=600)
            page.insert_image(fitz.Rect(0, 0, 800, 600), filename=str(img_path))
            doc.save(pdf_path)
            doc.close()

            logger.info("Created image-based PDF")

            # Test OCR extraction
            ocr_config = OCRConfig(lang="en")
            ocr_extractor = OCRExtractor(ocr_config)

            pages = ocr_extractor.extract_pdf_with_ocr(pdf_path)

            logger.info("\nOCR Results:")
            logger.info(f"Extracted {len(pages)} pages")

            if pages:
                page = pages[0]
                logger.info(f"Text blocks found: {len(page.text_blocks)}")

                for i, block in enumerate(page.text_blocks):
                    logger.info(f"\nBlock {i + 1}:")
                    logger.info(f"  Text: {block.text}")
                    logger.info(f"  Position: ({block.bbox[0]:.1f}, {block.bbox[1]:.1f})")
                    logger.info(f"  Font: {block.font_name} (size: {block.font_size:.1f})")

    except Exception as e:
        logger.error(f"Error in image PDF test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    logger.info("Testing OCR functionality...")

    # Test with existing PDFs
    test_ocr_extraction()

    # Test with created image PDF
    test_image_pdf_creation_and_ocr()

    logger.info("\nOCR demo completed!")
