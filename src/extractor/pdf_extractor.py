"""PDF text extraction module using PyMuPDF."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import fitz  # PyMuPDF  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Represents a text block with position information."""

    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page_num: int
    font_size: float
    font_name: str
    block_type: str = "text"  # text, title, paragraph, etc.


@dataclass
class PageInfo:
    """Information about a single page."""

    page_num: int
    width: float
    height: float
    text_blocks: List[TextBlock]
    raw_text: str
    has_images: bool = False


class PDFExtractor:
    """Extract text and structure from PDF files using PyMuPDF."""

    def __init__(self, max_pages: int = 50, use_ocr: bool = True):
        """Initialize PDF extractor.

        Args:
            max_pages: Maximum number of pages to process
            use_ocr: Whether to use OCR for image-based pages

        """
        self.max_pages = max_pages
        self.use_ocr = use_ocr
        self._ocr_extractor: Optional[Any] = None

    def extract_pdf(self, pdf_path: Path) -> List[PageInfo]:
        """Extract text and structure from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PageInfo objects containing extracted data

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF has too many pages

        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Opening PDF: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            # Check page count
            if len(doc) > self.max_pages:
                raise ValueError(f"PDF has {len(doc)} pages, maximum allowed is {self.max_pages}")

            pages = []

            for page_num in range(len(doc)):
                logger.debug(f"Processing page {page_num + 1}/{len(doc)}")
                page = doc[page_num]
                page_info = self._extract_page(page, page_num)
                pages.append(page_info)

            doc.close()
            logger.info(f"Successfully extracted {len(pages)} pages from PDF")
            return pages

        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            raise

    def _extract_page(self, page: fitz.Page, page_num: int) -> PageInfo:
        """Extract text and structure from a single page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-based)

        Returns:
            PageInfo object with extracted data

        """
        # Check if OCR is needed for this page
        if self.use_ocr and self._is_image_based_page(page):
            logger.info(f"Page {page_num + 1} appears to be image-based, using OCR")
            return self._extract_page_with_ocr(page, page_num)

        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Extract text blocks with formatting information
        text_blocks = self._extract_text_blocks(page, page_num)

        # Get raw text
        raw_text = page.get_text()

        # Check for images
        has_images = len(page.get_images()) > 0

        return PageInfo(
            page_num=page_num,
            width=width,
            height=height,
            text_blocks=text_blocks,
            raw_text=raw_text,
            has_images=has_images,
        )

    def _extract_text_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """Extract text blocks from a page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-based)

        Returns:
            List of TextBlock objects

        """
        text_blocks = []
        blocks = page.get_text("dict")

        for block in blocks["blocks"]:
            if "lines" in block:  # Text block
                text_block = self._process_text_block(block, page_num)
                if text_block:
                    text_blocks.append(text_block)

        return text_blocks

    def _process_text_block(self, block: Dict, page_num: int) -> Optional[TextBlock]:
        """Process a single text block.

        Args:
            block: Block dictionary from PyMuPDF
            page_num: Page number (0-based)

        Returns:
            TextBlock object or None if block is empty

        """
        block_text_parts = []

        for line in block["lines"]:
            line_text_parts = []

            for span in line["spans"]:
                text = span["text"].strip()
                if text:
                    line_text_parts.append(text)

            if line_text_parts:
                block_text_parts.append(" ".join(line_text_parts))

        if not block_text_parts:
            return None

        block_text = "\n".join(block_text_parts)

        # Get first span for font information
        first_span = self._get_first_span(block)
        if not first_span:
            return None

        return TextBlock(
            text=block_text,
            bbox=(
                block["bbox"][0],
                block["bbox"][1],
                block["bbox"][2],
                block["bbox"][3],
            ),
            page_num=page_num,
            font_size=first_span.get("size", 12.0),
            font_name=first_span.get("font", "Unknown"),
            block_type=self._classify_block_type(
                first_span.get("size", 12.0), block_text
            ),
        )

    def _get_first_span(self, block: Dict) -> Optional[Dict]:
        """Get the first span from a text block.

        Args:
            block: Block dictionary from PyMuPDF

        Returns:
            First span dictionary or None

        """
        for line in block["lines"]:
            if line["spans"]:
                return line["spans"][0]
        return None

    def _classify_block_type(self, font_size: float, text: str) -> str:
        """Classify text block type based on font size and content.

        Args:
            font_size: Font size of the text
            text: Text content

        Returns:
            Block type classification

        """
        # Simple heuristics for block classification
        if font_size > 16:
            return "title"
        elif font_size > 14:
            return "heading"
        elif len(text.split()) < 5:
            return "short_text"
        else:
            return "paragraph"

    def get_text_by_page(self, pages: List[PageInfo]) -> Dict[int, str]:
        """Get plain text for each page.

        Args:
            pages: List of PageInfo objects

        Returns:
            Dictionary mapping page numbers to text content

        """
        return {page.page_num: page.raw_text for page in pages}

    def get_text_blocks_by_page(self, pages: List[PageInfo]) -> Dict[int, List[TextBlock]]:
        """Get text blocks for each page.

        Args:
            pages: List of PageInfo objects

        Returns:
            Dictionary mapping page numbers to text blocks

        """
        return {page.page_num: page.text_blocks for page in pages}

    def analyze_layout_structure(self, pages: List[PageInfo]) -> Dict[str, Any]:
        """Analyze basic layout structure of the document.

        Args:
            pages: List of PageInfo objects

        Returns:
            Dictionary with layout analysis results

        """
        if not pages:
            return {}

        analysis = {
            "total_pages": len(pages),
            "average_page_width": sum(page.width for page in pages) / len(pages),
            "average_page_height": sum(page.height for page in pages) / len(pages),
            "pages_with_images": sum(1 for page in pages if page.has_images),
            "total_text_blocks": sum(len(page.text_blocks) for page in pages),
            "font_sizes": set(),  # type: ignore
            "font_names": set(),  # type: ignore
            "block_types": {},
        }

        # Collect font information and block types
        for page in pages:
            for block in page.text_blocks:
                font_sizes_set: Set[float] = analysis["font_sizes"]
                font_names_set: Set[str] = analysis["font_names"]
                font_sizes_set.add(block.font_size)
                font_names_set.add(block.font_name)

                block_type = block.block_type
                block_types_dict: Dict[str, int] = analysis["block_types"]
                if block_type not in block_types_dict:
                    block_types_dict[block_type] = 0
                block_types_dict[block_type] += 1

        # Convert sets to sorted lists for JSON serialization
        font_sizes_set: Set[float] = analysis["font_sizes"]
        font_names_set: Set[str] = analysis["font_names"]
        analysis["font_sizes"] = sorted(list(font_sizes_set))
        analysis["font_names"] = sorted(list(font_names_set))

        return analysis

    def _is_image_based_page(self, page: fitz.Page) -> bool:
        """Check if a page is image-based (requires OCR).

        Args:
            page: PyMuPDF page object

        Returns:
            True if page is image-based and requires OCR

        """
        # Check if page has minimal text but has images
        text = page.get_text().strip()
        has_images = len(page.get_images()) > 0

        # If no text but has images, it's likely image-based
        if not text and has_images:
            return True

        # If very little text compared to page size, might be image-based
        if has_images and len(text) < 100:
            return True

        return False

    def _extract_page_with_ocr(self, page: fitz.Page, page_num: int) -> PageInfo:
        """Extract text from a page using OCR.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-based)

        Returns:
            PageInfo object with OCR-extracted text

        """
        if self._ocr_extractor is None:
            from .ocr_extractor import OCRExtractor
            self._ocr_extractor = OCRExtractor()

        return self._ocr_extractor.extract_page_ocr(page, page_num)
