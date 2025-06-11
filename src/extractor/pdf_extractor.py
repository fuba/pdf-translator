"""PDF text extraction module using PyMuPDF."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

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

    def __init__(self, max_pages: int = 50):
        """Initialize PDF extractor

        Args:
            max_pages: Maximum number of pages to process

        """
        self.max_pages = max_pages

    def extract_pdf(self, pdf_path: Path) -> List[PageInfo]:
        """Extract text and structure from PDF file

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
        """Extract text and structure from a single page

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-based)

        Returns:
            PageInfo object with extracted data

        """
        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Extract text blocks with formatting information
        text_blocks = []
        blocks = page.get_text("dict")

        for block in blocks["blocks"]:
            if "lines" in block:  # Text block
                block_text_parts = []

                for line in block["lines"]:
                    line_text_parts = []

                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            line_text_parts.append(text)

                    if line_text_parts:
                        block_text_parts.append(" ".join(line_text_parts))

                if block_text_parts:
                    block_text = "\n".join(block_text_parts)

                    # Get first span for font information
                    first_span = None
                    for line in block["lines"]:
                        if line["spans"]:
                            first_span = line["spans"][0]
                            break

                    if first_span:
                        text_block = TextBlock(
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
                        text_blocks.append(text_block)

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

    def _classify_block_type(self, font_size: float, text: str) -> str:
        """Classify text block type based on font size and content

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
        """Get plain text for each page

        Args:
            pages: List of PageInfo objects

        Returns:
            Dictionary mapping page numbers to text content

        """
        return {page.page_num: page.raw_text for page in pages}

    def get_text_blocks_by_page(self, pages: List[PageInfo]) -> Dict[int, List[TextBlock]]:
        """Get text blocks for each page

        Args:
            pages: List of PageInfo objects

        Returns:
            Dictionary mapping page numbers to text blocks

        """
        return {page.page_num: page.text_blocks for page in pages}

    def analyze_layout_structure(self, pages: List[PageInfo]) -> Dict[str, Any]:
        """Analyze basic layout structure of the document

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
