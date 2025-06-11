"""Document layout analysis module using LayoutLMv3 and DiT models."""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from transformers import AutoProcessor

from ..extractor.pdf_extractor import PageInfo, TextBlock

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Layout region types based on common document structures."""

    TEXT = "text"
    TITLE = "title"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    FIGURE = "figure"
    HEADER = "header"
    FOOTER = "footer"
    COLUMN = "column"
    SECTION = "section"


@dataclass
class LayoutRegion:
    """Represents a detected layout region with semantic information."""

    region_type: RegionType
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    confidence: float
    page_num: int
    text_blocks: List[TextBlock]
    column_index: Optional[int] = None  # For multi-column layouts


@dataclass
class LayoutAnalysisResult:
    """Result of layout analysis for a single page."""

    page_num: int
    page_width: float
    page_height: float
    regions: List[LayoutRegion]
    column_count: int = 1
    has_tables: bool = False
    has_figures: bool = False


class LayoutAnalyzerConfig:
    """Configuration for layout analyzer."""

    def __init__(
        self,
        model_name: str = "microsoft/layoutlmv3-base",
        confidence_threshold: float = 0.5,
        use_gpu: bool = True,
        max_image_size: int = 1024,
        column_detection_enabled: bool = True,
    ):
        """Initialize layout analyzer configuration.
        
        Args:
            model_name: HuggingFace model name for layout analysis
            confidence_threshold: Minimum confidence for region detection
            use_gpu: Whether to use GPU if available
            max_image_size: Maximum image size for processing
            column_detection_enabled: Whether to detect column layouts

        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.max_image_size = max_image_size
        self.column_detection_enabled = column_detection_enabled
        self.device = "cuda" if self.use_gpu else "cpu"


class LayoutAnalyzer:
    """Document layout analyzer using pre-trained models."""

    def __init__(self, config: Optional[LayoutAnalyzerConfig] = None):
        """Initialize layout analyzer.
        
        Args:
            config: Layout analyzer configuration

        """
        self.config = config or LayoutAnalyzerConfig()
        self.model = None
        self.processor = None
        self._model_loaded = False

    def _load_model(self) -> None:
        """Load the layout analysis model lazily."""
        if self._model_loaded:
            return

        try:
            logger.info(f"Loading layout analysis model: {self.config.model_name}")

            # Try to load LayoutLMv3 for object detection
            # Note: This is a simplified approach - in practice, you might need
            # a specialized model fine-tuned for layout detection
            self.processor = AutoProcessor.from_pretrained(
                self.config.model_name,
                apply_ocr=False  # We already have text from PDFExtractor
            )

            # For now, we'll use a fallback approach with basic layout rules
            # TODO: Integrate actual LayoutLMv3 or DiT model for object detection
            logger.warning(
                "Using fallback layout analysis - full LayoutLMv3/DiT integration pending"
            )

            self._model_loaded = True

        except Exception as e:
            logger.error(f"Failed to load layout model: {e}")
            logger.info("Falling back to rule-based layout analysis")
            self._model_loaded = True

    def analyze_page_layout(
        self,
        page_info: PageInfo,
        pdf_path: Optional[Path] = None
    ) -> LayoutAnalysisResult:
        """Analyze layout of a single page.
        
        Args:
            page_info: Page information from PDFExtractor
            pdf_path: Optional path to PDF for image extraction
            
        Returns:
            Layout analysis result

        """
        self._load_model()

        # For now, implement rule-based layout analysis
        # TODO: Replace with actual ML-based detection
        regions = self._analyze_layout_rules(page_info)

        # Detect column layout
        column_count = self._detect_columns(page_info) if self.config.column_detection_enabled else 1

        # Check for tables and figures
        has_tables = any(r.region_type == RegionType.TABLE for r in regions)
        has_figures = any(r.region_type == RegionType.FIGURE for r in regions)

        return LayoutAnalysisResult(
            page_num=page_info.page_num,
            page_width=page_info.width,
            page_height=page_info.height,
            regions=regions,
            column_count=column_count,
            has_tables=has_tables,
            has_figures=has_figures
        )

    def _analyze_layout_rules(self, page_info: PageInfo) -> List[LayoutRegion]:
        """Rule-based layout analysis (fallback method).
        
        Args:
            page_info: Page information
            
        Returns:
            List of detected regions

        """
        regions = []

        # Sort text blocks by vertical position
        sorted_blocks = sorted(page_info.text_blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

        for block in sorted_blocks:
            # Determine region type based on text characteristics
            region_type = self._classify_text_block(block, page_info)

            region = LayoutRegion(
                region_type=region_type,
                bbox=block.bbox,
                confidence=0.8,  # Rule-based confidence
                page_num=block.page_num,
                text_blocks=[block]
            )

            regions.append(region)

        return regions

    def _classify_text_block(self, block: TextBlock, page_info: PageInfo) -> RegionType:
        """Classify text block based on characteristics.
        
        Args:
            block: Text block to classify
            page_info: Page information for context
            
        Returns:
            Classified region type

        """
        # Simple heuristics for text classification
        text = block.text.strip()

        # Check for lists (starts with bullet points or numbers) - highest priority
        if (text.startswith(('•', '●', '○', '-', '*')) or
            (len(text) > 2 and text[0].isdigit() and text[1] in '.)')):
            return RegionType.LIST

        # Check for titles (larger font, shorter text) - only if we have other blocks for comparison
        if len(page_info.text_blocks) > 1:
            avg_font_size = sum(b.font_size for b in page_info.text_blocks) / len(page_info.text_blocks)
            if block.font_size >= avg_font_size * 1.25 and len(text) < 100:  # More lenient threshold
                return RegionType.TITLE
        elif block.font_size > 14.0 and len(text) < 100:  # Fallback for single block pages
            return RegionType.TITLE

        # Check for headers/footers (position-based) - lower priority than content-based
        page_height = page_info.height
        if block.bbox[1] < page_height * 0.05:  # Top 5% (more restrictive)
            return RegionType.HEADER
        elif block.bbox[3] > page_height * 0.95:  # Bottom 5% (more restrictive)
            return RegionType.FOOTER

        # Default to paragraph
        return RegionType.PARAGRAPH

    def _detect_columns(self, page_info: PageInfo) -> int:
        """Detect number of columns in the page layout.
        
        Args:
            page_info: Page information
            
        Returns:
            Number of detected columns

        """
        if not page_info.text_blocks:
            return 1

        # Group text blocks by horizontal position (left edge)
        x_positions = [block.bbox[0] for block in page_info.text_blocks]

        # Sort unique x positions
        unique_x = sorted(set(x_positions))

        # If only one unique x position, it's single column
        if len(unique_x) <= 1:
            return 1

        # Calculate gaps between consecutive x positions
        gaps = [unique_x[i+1] - unique_x[i] for i in range(len(unique_x)-1)]

        if not gaps:
            return 1

        # Count blocks at each x position to determine if it's a real column
        x_position_counts = {}
        for x in x_positions:
            x_position_counts[x] = x_position_counts.get(x, 0) + 1

        # Only consider x positions with multiple blocks as potential column starts
        significant_x_positions = [x for x, count in x_position_counts.items() if count >= 2]
        significant_x_positions.sort()

        if len(significant_x_positions) <= 1:
            return 1

        # Check gaps between significant positions
        column_gaps = [
            significant_x_positions[i+1] - significant_x_positions[i]
            for i in range(len(significant_x_positions)-1)
        ]

        # Use a more lenient threshold for column detection
        avg_gap = sum(gaps) / len(gaps)
        # For multi-column detection, use a threshold that's reasonable for column separation
        significant_gap_threshold = max(150, avg_gap * 0.8)  # At least 150 units or 80% of average gap

        # Count large gaps as column separators
        large_gaps = [g for g in column_gaps if g >= significant_gap_threshold]

        return len(large_gaps) + 1

    def analyze_document_layout(
        self,
        pages: List[PageInfo],
        pdf_path: Optional[Path] = None
    ) -> List[LayoutAnalysisResult]:
        """Analyze layout for multiple pages.
        
        Args:
            pages: List of page information
            pdf_path: Optional path to PDF file
            
        Returns:
            List of layout analysis results

        """
        results = []

        for page_info in pages:
            try:
                result = self.analyze_page_layout(page_info, pdf_path)
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to analyze layout for page {page_info.page_num}: {e}")
                # Create fallback result
                fallback_result = LayoutAnalysisResult(
                    page_num=page_info.page_num,
                    page_width=page_info.width,
                    page_height=page_info.height,
                    regions=[],
                    column_count=1,
                    has_tables=False,
                    has_figures=False
                )
                results.append(fallback_result)

        return results

    def get_text_by_region_type(
        self,
        results: List[LayoutAnalysisResult],
        region_type: RegionType
    ) -> Dict[int, List[str]]:
        """Extract text by region type across all pages.
        
        Args:
            results: Layout analysis results
            region_type: Type of region to extract
            
        Returns:
            Dictionary of page_num -> list of texts

        """
        text_by_page = {}

        for result in results:
            page_texts = []
            for region in result.regions:
                if region.region_type == region_type:
                    region_texts = [block.text for block in region.text_blocks]
                    page_texts.extend(region_texts)

            if page_texts:
                text_by_page[result.page_num] = page_texts

        return text_by_page
