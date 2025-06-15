"""Tests for PDF extractor module."""

from pathlib import Path

import pytest

from pdf_translator.extractor import PageInfo, PDFExtractor, TextBlock


class TestPDFExtractor:
    """Test cases for PDFExtractor class."""

    def test_init_default(self):
        """Test PDFExtractor initialization with default parameters."""
        extractor = PDFExtractor()
        assert extractor.max_pages == 50
        assert extractor.use_ocr is True

    def test_init_custom_max_pages(self):
        """Test PDFExtractor initialization with custom max_pages."""
        extractor = PDFExtractor(max_pages=100)
        assert extractor.max_pages == 100

    def test_init_without_ocr(self):
        """Test PDFExtractor initialization with OCR disabled."""
        extractor = PDFExtractor(use_ocr=False)
        assert extractor.use_ocr is False
        assert extractor._ocr_extractor is None

    def test_extract_pdf_file_not_found(self):
        """Test extract_pdf with non-existent file."""
        extractor = PDFExtractor()
        non_existent_path = Path("non_existent_file.pdf")

        with pytest.raises(FileNotFoundError):
            extractor.extract_pdf(non_existent_path)

    def test_extract_pdf_too_many_pages(self, large_pdf):
        """Test extract_pdf with PDF exceeding page limit."""
        extractor = PDFExtractor(max_pages=50)

        with pytest.raises(ValueError, match="PDF has .* pages, maximum allowed is 50"):
            extractor.extract_pdf(large_pdf)

    def test_extract_pdf_success(self, sample_pdf):
        """Test successful PDF extraction."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(sample_pdf)

        assert len(pages) == 2
        assert all(isinstance(page, PageInfo) for page in pages)
        assert pages[0].page_num == 0
        assert pages[1].page_num == 1

    def test_extract_pdf_empty_page(self, empty_pdf):
        """Test extraction from empty PDF."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(empty_pdf)

        assert len(pages) == 1
        assert pages[0].page_num == 0
        assert len(pages[0].text_blocks) == 0
        assert pages[0].raw_text.strip() == ""

    def test_page_info_structure(self, sample_pdf):
        """Test PageInfo structure and content."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(sample_pdf)

        page = pages[0]
        assert hasattr(page, "page_num")
        assert hasattr(page, "width")
        assert hasattr(page, "height")
        assert hasattr(page, "text_blocks")
        assert hasattr(page, "raw_text")
        assert hasattr(page, "has_images")

        assert page.width > 0
        assert page.height > 0
        assert isinstance(page.text_blocks, list)
        assert isinstance(page.raw_text, str)
        assert isinstance(page.has_images, bool)

    def test_text_block_structure(self, sample_pdf):
        """Test TextBlock structure and content."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(sample_pdf)

        # Find a page with text blocks
        text_blocks = None
        for page in pages:
            if page.text_blocks:
                text_blocks = page.text_blocks
                break

        assert text_blocks is not None, "No text blocks found in sample PDF"

        block = text_blocks[0]
        assert hasattr(block, "text")
        assert hasattr(block, "bbox")
        assert hasattr(block, "page_num")
        assert hasattr(block, "font_size")
        assert hasattr(block, "font_name")
        assert hasattr(block, "block_type")

        assert isinstance(block.text, str)
        assert len(block.bbox) == 4  # (x0, y0, x1, y1)
        assert isinstance(block.page_num, int)
        assert isinstance(block.font_size, float)
        assert isinstance(block.font_name, str)
        assert isinstance(block.block_type, str)

    def test_get_text_by_page(self, sample_pdf):
        """Test get_text_by_page method."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(sample_pdf)
        text_by_page = extractor.get_text_by_page(pages)

        assert isinstance(text_by_page, dict)
        assert len(text_by_page) == 2
        assert 0 in text_by_page
        assert 1 in text_by_page
        assert "Test Document" in text_by_page[0]
        assert "Chapter 1" in text_by_page[1]

    def test_get_text_blocks_by_page(self, sample_pdf):
        """Test get_text_blocks_by_page method."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(sample_pdf)
        blocks_by_page = extractor.get_text_blocks_by_page(pages)

        assert isinstance(blocks_by_page, dict)
        assert len(blocks_by_page) == 2
        assert 0 in blocks_by_page
        assert 1 in blocks_by_page
        assert all(
            isinstance(block, TextBlock) for blocks in blocks_by_page.values() for block in blocks
        )

    def test_analyze_layout_structure(self, sample_pdf):
        """Test analyze_layout_structure method."""
        extractor = PDFExtractor()
        pages = extractor.extract_pdf(sample_pdf)
        analysis = extractor.analyze_layout_structure(pages)

        assert isinstance(analysis, dict)
        assert "total_pages" in analysis
        assert "average_page_width" in analysis
        assert "average_page_height" in analysis
        assert "pages_with_images" in analysis
        assert "total_text_blocks" in analysis
        assert "font_sizes" in analysis
        assert "font_names" in analysis
        assert "block_types" in analysis

        assert analysis["total_pages"] == 2
        assert analysis["average_page_width"] > 0
        assert analysis["average_page_height"] > 0
        assert isinstance(analysis["font_sizes"], list)
        assert isinstance(analysis["font_names"], list)
        assert isinstance(analysis["block_types"], dict)

    def test_analyze_layout_structure_empty(self):
        """Test analyze_layout_structure with empty pages list."""
        extractor = PDFExtractor()
        analysis = extractor.analyze_layout_structure([])

        assert analysis == {}

    def test_classify_block_type(self):
        """Test _classify_block_type method."""
        extractor = PDFExtractor()

        # Test title classification
        assert extractor._classify_block_type(18.0, "Main Title") == "title"

        # Test heading classification
        assert extractor._classify_block_type(15.0, "Chapter Heading") == "heading"

        # Test short text classification
        assert extractor._classify_block_type(12.0, "Short") == "short_text"

        # Test paragraph classification
        assert (
            extractor._classify_block_type(12.0, "This is a longer paragraph with multiple words")
            == "paragraph"
        )


class TestTextBlock:
    """Test cases for TextBlock dataclass."""

    def test_text_block_creation(self):
        """Test TextBlock creation and attributes."""
        block = TextBlock(
            text="Sample text",
            bbox=(10.0, 20.0, 100.0, 50.0),
            page_num=0,
            font_size=12.0,
            font_name="Arial",
            block_type="paragraph",
        )

        assert block.text == "Sample text"
        assert block.bbox == (10.0, 20.0, 100.0, 50.0)
        assert block.page_num == 0
        assert block.font_size == 12.0
        assert block.font_name == "Arial"
        assert block.block_type == "paragraph"

    def test_text_block_default_type(self):
        """Test TextBlock with default block_type."""
        block = TextBlock(
            text="Sample text",
            bbox=(10.0, 20.0, 100.0, 50.0),
            page_num=0,
            font_size=12.0,
            font_name="Arial",
        )

        assert block.block_type == "text"


class TestPageInfo:
    """Test cases for PageInfo dataclass."""

    def test_page_info_creation(self):
        """Test PageInfo creation and attributes."""
        text_blocks = [TextBlock("Sample text", (0, 0, 100, 20), 0, 12.0, "Arial")]

        page = PageInfo(
            page_num=0,
            width=595.0,
            height=842.0,
            text_blocks=text_blocks,
            raw_text="Sample text",
            has_images=False,
        )

        assert page.page_num == 0
        assert page.width == 595.0
        assert page.height == 842.0
        assert page.text_blocks == text_blocks
        assert page.raw_text == "Sample text"
        assert page.has_images is False

    def test_page_info_default_images(self):
        """Test PageInfo with default has_images."""
        page = PageInfo(page_num=0, width=595.0, height=842.0, text_blocks=[], raw_text="")

        assert page.has_images is False

    def test_is_image_based_page(self, sample_pdf):
        """Test _is_image_based_page method."""
        extractor = PDFExtractor()
        import fitz

        doc = fitz.open(sample_pdf)

        # Test with text page (should be False)
        page = doc[0]
        assert extractor._is_image_based_page(page) is False

        doc.close()

    def test_extract_with_ocr_fallback(self, tmp_path):
        """Test extraction with OCR fallback for image pages."""
        from unittest.mock import patch

        # Create a mock image-based PDF page
        extractor = PDFExtractor(use_ocr=True)

        # Create PDF with mock image page
        import fitz

        pdf_path = tmp_path / "test_ocr.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(pdf_path)
        doc.close()

        # Mock the OCR functionality
        with patch.object(extractor, "_is_image_based_page", return_value=True):
            with patch.object(extractor, "_extract_page_with_ocr") as mock_ocr:
                mock_page_info = PageInfo(
                    page_num=0,
                    width=595.0,
                    height=842.0,
                    text_blocks=[TextBlock("OCR text", (0, 0, 100, 20), 0, 12.0, "OCR")],
                    raw_text="OCR text",
                    has_images=True,
                )
                mock_ocr.return_value = mock_page_info

                pages = extractor.extract_pdf(pdf_path)

                assert len(pages) == 1
                assert pages[0].raw_text == "OCR text"
                assert pages[0].has_images is True
                mock_ocr.assert_called_once()
