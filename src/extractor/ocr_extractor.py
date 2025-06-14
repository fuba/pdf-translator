"""OCR text extraction module using PaddleOCR for image-based PDFs."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF  # type: ignore
import numpy as np
from paddleocr import PaddleOCR  # type: ignore
from PIL import Image

from .pdf_extractor import PageInfo, TextBlock

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    """Configuration for OCR extraction."""

    lang: str = "en"  # Language for OCR (en, ch, japan, etc.)
    use_angle_cls: bool = True  # Enable angle classification
    det: bool = True  # Enable text detection
    rec: bool = True  # Enable text recognition
    cls: bool = True  # Enable text direction classification
    use_gpu: bool = False  # Use GPU for inference
    show_log: bool = False  # Show PaddleOCR logs
    drop_score: float = 0.5  # Drop results below this confidence score


class OCRExtractor:
    """Extract text from image-based PDFs using OCR."""

    def __init__(self, config: Optional[OCRConfig] = None):
        """Initialize OCR extractor.

        Args:
            config: OCR configuration

        """
        self.config = config or OCRConfig()
        self._ocr: Optional[PaddleOCR] = None

    def _get_ocr(self) -> PaddleOCR:
        """Get or create PaddleOCR instance (lazy loading).

        Returns:
            PaddleOCR instance

        """
        if self._ocr is None:
            logger.info("Initializing PaddleOCR...")
            self._ocr = PaddleOCR(
                lang=self.config.lang,
                use_angle_cls=self.config.use_angle_cls,
                det=self.config.det,
                rec=self.config.rec,
                cls=self.config.cls,
                use_gpu=self.config.use_gpu,
                show_log=self.config.show_log,
            )
            logger.info("PaddleOCR initialized successfully")
        return self._ocr

    def extract_page_ocr(self, page: fitz.Page, page_num: int) -> PageInfo:
        """Extract text from a page using OCR.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-based)

        Returns:
            PageInfo object with OCR-extracted text

        """
        # Convert page to image
        mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        # Convert to PIL Image then to numpy array
        import io
        img = Image.open(io.BytesIO(img_data))
        img_array = np.array(img)

        # Get page dimensions
        rect = page.rect
        width, height = rect.width, rect.height

        # Run OCR
        ocr = self._get_ocr()
        result = ocr.ocr(img_array, cls=self.config.cls)

        text_blocks = []
        raw_text_parts = []

        if result and result[0]:  # Check if OCR found any text
            for _idx, line in enumerate(result[0]):
                # Each line contains [box_points, (text, confidence)]
                box_points = line[0]
                text, confidence = line[1]

                # Skip low confidence results
                if confidence < self.config.drop_score:
                    continue

                # Convert box points to bbox
                # box_points is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [point[0] for point in box_points]
                y_coords = [point[1] for point in box_points]

                # Scale coordinates back to original page size (we used 2x zoom)
                x0 = min(x_coords) / 2
                y0 = min(y_coords) / 2
                x1 = max(x_coords) / 2
                y1 = max(y_coords) / 2

                # Estimate font size based on bbox height
                font_size = (y1 - y0) * 0.75  # Rough estimation

                text_block = TextBlock(
                    text=text,
                    bbox=(x0, y0, x1, y1),
                    page_num=page_num,
                    font_size=font_size,
                    font_name="OCR",
                    block_type=self._classify_block_type(font_size, text),
                )
                text_blocks.append(text_block)
                raw_text_parts.append(text)

        # Sort text blocks by position (top to bottom, left to right)
        text_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))

        # Combine raw text
        raw_text = "\n".join(raw_text_parts) if raw_text_parts else ""

        return PageInfo(
            page_num=page_num,
            width=width,
            height=height,
            text_blocks=text_blocks,
            raw_text=raw_text,
            has_images=True,  # OCR pages always have images
        )

    def _classify_block_type(self, font_size: float, text: str) -> str:
        """Classify text block type based on font size and content.

        Args:
            font_size: Estimated font size
            text: Text content

        Returns:
            Block type classification

        """
        # Simple heuristics for OCR text classification
        if font_size > 20:
            return "title"
        elif font_size > 16:
            return "heading"
        elif len(text.split()) < 5:
            return "short_text"
        else:
            return "paragraph"

    def is_image_based_page(self, page: fitz.Page) -> bool:
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

    def extract_pdf_with_ocr(self, pdf_path: Path, max_pages: int = 50) -> List[PageInfo]:
        """Extract text from PDF using OCR where needed.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to process

        Returns:
            List of PageInfo objects with extracted text

        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Opening PDF for OCR extraction: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            # Check page count
            if len(doc) > max_pages:
                raise ValueError(f"PDF has {len(doc)} pages, maximum allowed is {max_pages}")

            pages = []

            for page_num in range(len(doc)):
                logger.debug(f"Processing page {page_num + 1}/{len(doc)} with OCR")
                page = doc[page_num]

                if self.is_image_based_page(page):
                    logger.info(f"Page {page_num + 1} requires OCR")
                    page_info = self.extract_page_ocr(page, page_num)
                else:
                    # Use regular text extraction for text-based pages
                    from .pdf_extractor import PDFExtractor
                    extractor = PDFExtractor()
                    page_info = extractor._extract_page(page, page_num)

                pages.append(page_info)

            doc.close()
            logger.info(f"Successfully extracted {len(pages)} pages with OCR")
            return pages

        except Exception as e:
            logger.error(f"Error extracting PDF with OCR: {e}")
            raise
