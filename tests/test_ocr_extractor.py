"""Tests for OCR text extraction functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

from pdf_translator.extractor.ocr_extractor import OCRConfig, OCRExtractor
from pdf_translator.extractor.pdf_extractor import PageInfo


class TestOCRConfig:
    """Test OCR configuration."""

    def test_default_config(self):
        """Test default OCR configuration values."""
        config = OCRConfig()
        assert config.lang == "en"
        assert config.use_angle_cls is True
        assert config.det is True
        assert config.rec is True
        assert config.cls is True
        assert config.use_gpu is False
        assert config.show_log is False
        assert config.drop_score == 0.5

    def test_custom_config(self):
        """Test custom OCR configuration."""
        config = OCRConfig(
            lang="ch",
            use_gpu=True,
            drop_score=0.7,
        )
        assert config.lang == "ch"
        assert config.use_gpu is True
        assert config.drop_score == 0.7


class TestOCRExtractor:
    """Test OCR extractor functionality."""

    @pytest.fixture
    def ocr_extractor(self):
        """Create OCR extractor instance."""
        return OCRExtractor()

    @pytest.fixture
    def image_pdf(self, tmp_path):
        """Create a PDF with image content."""
        # Create an image with text
        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)

        # Try to use a basic font, fallback to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        except:
            font = ImageFont.load_default()

        # Draw text
        draw.text((50, 50), "OCR Test Title", fill="black", font=font)
        draw.text((50, 150), "This is a test document for OCR.", fill="black", font=font)
        draw.text((50, 250), "It contains multiple lines of text.", fill="black", font=font)

        # Save as image
        img_path = tmp_path / "test_image.png"
        img.save(img_path)

        # Create PDF with the image
        pdf_path = tmp_path / "image_pdf.pdf"
        doc = fitz.open()
        page = doc.new_page(width=800, height=600)
        page.insert_image(fitz.Rect(0, 0, 800, 600), filename=str(img_path))
        doc.save(pdf_path)
        doc.close()

        return pdf_path

    def test_init_default_config(self, ocr_extractor):
        """Test OCR extractor initialization with default config."""
        assert ocr_extractor.config.lang == "en"
        assert ocr_extractor._ocr is None  # Lazy loading

    def test_init_custom_config(self):
        """Test OCR extractor initialization with custom config."""
        config = OCRConfig(lang="japan", use_gpu=True)
        extractor = OCRExtractor(config)
        assert extractor.config.lang == "japan"
        assert extractor.config.use_gpu is True

    @patch("pdf_translator.extractor.ocr_extractor.PaddleOCR")
    def test_get_ocr_lazy_loading(self, mock_paddle_ocr, ocr_extractor):
        """Test lazy loading of PaddleOCR instance."""
        mock_ocr_instance = MagicMock()
        mock_paddle_ocr.return_value = mock_ocr_instance

        # First call should create instance
        ocr1 = ocr_extractor._get_ocr()
        assert ocr1 == mock_ocr_instance
        mock_paddle_ocr.assert_called_once()

        # Second call should return same instance
        ocr2 = ocr_extractor._get_ocr()
        assert ocr2 == mock_ocr_instance
        assert mock_paddle_ocr.call_count == 1  # Not called again

    def test_classify_block_type(self, ocr_extractor):
        """Test block type classification for OCR text."""
        assert ocr_extractor._classify_block_type(25, "Title") == "title"
        assert ocr_extractor._classify_block_type(18, "Heading") == "heading"
        assert ocr_extractor._classify_block_type(12, "Short") == "short_text"
        assert (
            ocr_extractor._classify_block_type(12, "This is a longer paragraph with multiple words")
            == "paragraph"
        )

    def test_is_image_based_page(self, ocr_extractor, image_pdf):
        """Test detection of image-based pages."""
        doc = fitz.open(image_pdf)
        page = doc[0]

        # Mock page methods for testing
        page.get_text = MagicMock(return_value="")
        page.get_images = MagicMock(return_value=[("img", 0, 0)])

        assert ocr_extractor.is_image_based_page(page) is True

        # Test text-based page (no images)
        page.get_text = MagicMock(
            return_value="This is a long text content that indicates text-based page"
        )
        page.get_images = MagicMock(return_value=[])  # No images
        assert ocr_extractor.is_image_based_page(page) is False

        doc.close()

    @patch("pdf_translator.extractor.ocr_extractor.PaddleOCR")
    def test_extract_page_ocr(self, mock_paddle_ocr, ocr_extractor, image_pdf):
        """Test OCR extraction from a single page."""
        # Mock OCR results
        mock_ocr_instance = MagicMock()
        mock_ocr_result = [
            [
                [[[100, 50], [300, 50], [300, 100], [100, 100]], ("OCR Test Title", 0.95)],
                [
                    [[100, 150], [500, 150], [500, 200], [100, 200]],
                    ("This is a test document for OCR.", 0.92),
                ],
                [
                    [[100, 250], [400, 250], [400, 300], [100, 300]],
                    ("Low confidence text", 0.3),
                ],  # Below threshold
            ]
        ]
        mock_ocr_instance.ocr.return_value = mock_ocr_result
        mock_paddle_ocr.return_value = mock_ocr_instance

        doc = fitz.open(image_pdf)
        page = doc[0]

        page_info = ocr_extractor.extract_page_ocr(page, 0)

        assert isinstance(page_info, PageInfo)
        assert page_info.page_num == 0
        assert page_info.has_images is True
        assert len(page_info.text_blocks) == 2  # Only high confidence results

        # Check first text block
        block1 = page_info.text_blocks[0]
        assert block1.text == "OCR Test Title"
        assert block1.font_name == "OCR"
        assert block1.page_num == 0

        # Check second text block
        block2 = page_info.text_blocks[1]
        assert block2.text == "This is a test document for OCR."

        doc.close()

    @patch("pdf_translator.extractor.ocr_extractor.PaddleOCR")
    def test_extract_pdf_with_ocr(self, mock_paddle_ocr, ocr_extractor, image_pdf):
        """Test full PDF extraction with OCR."""
        # Mock OCR results
        mock_ocr_instance = MagicMock()
        mock_ocr_result = [
            [
                [[[100, 50], [300, 50], [300, 100], [100, 100]], ("OCR Test Title", 0.95)],
            ]
        ]
        mock_ocr_instance.ocr.return_value = mock_ocr_result
        mock_paddle_ocr.return_value = mock_ocr_instance

        pages = ocr_extractor.extract_pdf_with_ocr(image_pdf)

        assert len(pages) == 1
        assert pages[0].has_images is True
        assert len(pages[0].text_blocks) > 0

    def test_extract_pdf_with_ocr_file_not_found(self, ocr_extractor):
        """Test OCR extraction with non-existent file."""
        with pytest.raises(FileNotFoundError):
            ocr_extractor.extract_pdf_with_ocr(Path("nonexistent.pdf"))

    def test_extract_pdf_with_ocr_too_many_pages(self, ocr_extractor, tmp_path):
        """Test OCR extraction with too many pages."""
        # Create PDF with many pages
        pdf_path = tmp_path / "many_pages.pdf"
        doc = fitz.open()
        for _ in range(60):
            doc.new_page()
        doc.save(pdf_path)
        doc.close()

        with pytest.raises(ValueError, match="maximum allowed is 50"):
            ocr_extractor.extract_pdf_with_ocr(pdf_path)

    @patch("pdf_translator.extractor.ocr_extractor.PaddleOCR")
    def test_extract_mixed_pdf(self, mock_paddle_ocr, ocr_extractor, tmp_path):
        """Test extraction of PDF with mixed text and image pages."""
        # Create mixed PDF
        pdf_path = tmp_path / "mixed.pdf"
        doc = fitz.open()

        # Add text page
        page1 = doc.new_page()
        page1.insert_text((50, 50), "This is text-based content")

        # Add image page
        doc.new_page()
        # Simulate image page (no text)

        doc.save(pdf_path)
        doc.close()

        # Mock OCR for image page
        mock_ocr_instance = MagicMock()
        mock_ocr_result = [
            [
                [[[100, 50], [300, 50], [300, 100], [100, 100]], ("Image page text", 0.95)],
            ]
        ]
        mock_ocr_instance.ocr.return_value = mock_ocr_result
        mock_paddle_ocr.return_value = mock_ocr_instance

        # Mock is_image_based_page to return True for page 2
        with patch.object(ocr_extractor, "is_image_based_page") as mock_is_image:
            mock_is_image.side_effect = [False, True]  # First page text, second page image

            pages = ocr_extractor.extract_pdf_with_ocr(pdf_path)

            assert len(pages) == 2
            # First page should have regular text extraction
            assert pages[0].raw_text.strip() == "This is text-based content"
            # Second page should have OCR text
            assert any("Image page text" in block.text for block in pages[1].text_blocks)
