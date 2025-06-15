"""Tests for layout analyzer module."""

from unittest.mock import patch

from pdf_translator.extractor.pdf_extractor import PageInfo, TextBlock
from pdf_translator.layout_analyzer import (
    LayoutAnalysisResult,
    LayoutAnalyzer,
    LayoutAnalyzerConfig,
    LayoutRegion,
    RegionType,
)


class TestLayoutAnalyzerConfig:
    """Test LayoutAnalyzerConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LayoutAnalyzerConfig()

        assert config.model_name == "microsoft/layoutlmv3-base"
        assert config.confidence_threshold == 0.5
        assert config.max_image_size == 1024
        assert config.column_detection_enabled is True
        assert config.device in ["cuda", "cpu"]

    def test_custom_config(self):
        """Test custom configuration values."""
        config = LayoutAnalyzerConfig(
            model_name="custom/model",
            confidence_threshold=0.7,
            use_gpu=False,
            max_image_size=512,
            column_detection_enabled=False,
        )

        assert config.model_name == "custom/model"
        assert config.confidence_threshold == 0.7
        assert config.use_gpu is False
        assert config.max_image_size == 512
        assert config.column_detection_enabled is False
        assert config.device == "cpu"


class TestLayoutAnalyzer:
    """Test LayoutAnalyzer class."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = LayoutAnalyzer()

        assert analyzer.config is not None
        assert analyzer.model is None
        assert analyzer.processor is None
        assert analyzer._model_loaded is False

    def test_initialization_with_config(self):
        """Test analyzer initialization with custom config."""
        config = LayoutAnalyzerConfig(confidence_threshold=0.8)
        analyzer = LayoutAnalyzer(config)

        assert analyzer.config.confidence_threshold == 0.8

    def test_classify_text_block_title(self):
        """Test title classification."""
        analyzer = LayoutAnalyzer()

        # Create mock text blocks for context
        text_blocks = [
            TextBlock("Normal text", (0, 100, 200, 120), 1, 12.0, "Arial"),
            TextBlock("Another normal text", (0, 130, 200, 150), 1, 12.0, "Arial"),
        ]

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=text_blocks,
            raw_text="test",
        )

        # Title block (larger font, shorter text)
        title_block = TextBlock("Chapter 1", (0, 50, 200, 80), 1, 18.0, "Arial")

        region_type = analyzer._classify_text_block(title_block, page_info)
        assert region_type == RegionType.TITLE

    def test_classify_text_block_header(self):
        """Test header classification based on position."""
        analyzer = LayoutAnalyzer()

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=[],
            raw_text="test",
        )

        # Header block (top 5% of page)
        header_block = TextBlock("Page Header", (0, 10, 200, 30), 1, 12.0, "Arial")

        region_type = analyzer._classify_text_block(header_block, page_info)
        assert region_type == RegionType.HEADER

    def test_classify_text_block_footer(self):
        """Test footer classification based on position."""
        analyzer = LayoutAnalyzer()

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=[],
            raw_text="test",
        )

        # Footer block (bottom 5% of page)
        footer_block = TextBlock("Page 1", (0, 770, 200, 790), 1, 10.0, "Arial")

        region_type = analyzer._classify_text_block(footer_block, page_info)
        assert region_type == RegionType.FOOTER

    def test_classify_text_block_list(self):
        """Test list item classification."""
        analyzer = LayoutAnalyzer()

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=[],
            raw_text="test",
        )

        # Test different list formats
        list_blocks = [
            TextBlock("• First item", (0, 100, 200, 120), 1, 12.0, "Arial"),
            TextBlock("- Second item", (0, 130, 200, 150), 1, 12.0, "Arial"),
            TextBlock("* Third item", (0, 160, 200, 180), 1, 12.0, "Arial"),
            TextBlock("1. Numbered item", (0, 190, 200, 210), 1, 12.0, "Arial"),
        ]

        for block in list_blocks:
            region_type = analyzer._classify_text_block(block, page_info)
            assert region_type == RegionType.LIST

    def test_classify_text_block_paragraph(self):
        """Test paragraph classification (default)."""
        analyzer = LayoutAnalyzer()

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=[],
            raw_text="test",
        )

        # Regular paragraph text
        para_block = TextBlock(
            "This is a regular paragraph with normal text content.",
            (0, 200, 400, 240),
            1,
            12.0,
            "Arial",
        )

        region_type = analyzer._classify_text_block(para_block, page_info)
        assert region_type == RegionType.PARAGRAPH

    def test_detect_columns_single(self):
        """Test single column detection."""
        analyzer = LayoutAnalyzer()

        # Single column layout
        text_blocks = [
            TextBlock("Text 1", (50, 100, 500, 120), 1, 12.0, "Arial"),
            TextBlock("Text 2", (50, 130, 500, 150), 1, 12.0, "Arial"),
            TextBlock("Text 3", (50, 160, 500, 180), 1, 12.0, "Arial"),
        ]

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=text_blocks,
            raw_text="test",
        )

        columns = analyzer._detect_columns(page_info)
        assert columns == 1

    def test_detect_columns_multiple(self):
        """Test multiple column detection."""
        analyzer = LayoutAnalyzer()

        # Two column layout
        text_blocks = [
            TextBlock("Left column 1", (50, 100, 200, 120), 1, 12.0, "Arial"),
            TextBlock("Right column 1", (350, 100, 500, 120), 1, 12.0, "Arial"),
            TextBlock("Left column 2", (50, 130, 200, 150), 1, 12.0, "Arial"),
            TextBlock("Right column 2", (350, 130, 500, 150), 1, 12.0, "Arial"),
        ]

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=text_blocks,
            raw_text="test",
        )

        columns = analyzer._detect_columns(page_info)
        assert columns == 2

    def test_detect_columns_empty_page(self):
        """Test column detection with empty page."""
        analyzer = LayoutAnalyzer()

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=[],
            raw_text="",
        )

        columns = analyzer._detect_columns(page_info)
        assert columns == 1

    def test_analyze_page_layout(self):
        """Test page layout analysis."""
        analyzer = LayoutAnalyzer()

        text_blocks = [
            TextBlock("Title", (50, 50, 400, 80), 1, 18.0, "Arial"),
            TextBlock("Paragraph 1", (50, 100, 400, 140), 1, 12.0, "Arial"),
            TextBlock("• List item", (50, 150, 400, 170), 1, 12.0, "Arial"),
        ]

        page_info = PageInfo(
            page_num=1,
            width=600,
            height=800,
            text_blocks=text_blocks,
            raw_text="test",
        )

        result = analyzer.analyze_page_layout(page_info)

        assert isinstance(result, LayoutAnalysisResult)
        assert result.page_num == 1
        assert result.page_width == 600
        assert result.page_height == 800
        assert len(result.regions) == 3
        assert result.column_count == 1
        assert result.has_tables is False
        assert result.has_figures is False

        # Check region types
        region_types = [r.region_type for r in result.regions]
        assert RegionType.TITLE in region_types
        assert RegionType.PARAGRAPH in region_types
        assert RegionType.LIST in region_types

    def test_analyze_document_layout(self):
        """Test multi-page document layout analysis."""
        analyzer = LayoutAnalyzer()

        pages = [
            PageInfo(
                page_num=1,
                width=600,
                height=800,
                text_blocks=[TextBlock("Page 1 content", (50, 100, 400, 120), 1, 12.0, "Arial")],
                raw_text="Page 1",
            ),
            PageInfo(
                page_num=2,
                width=600,
                height=800,
                text_blocks=[TextBlock("Page 2 content", (50, 100, 400, 120), 2, 12.0, "Arial")],
                raw_text="Page 2",
            ),
        ]

        results = analyzer.analyze_document_layout(pages)

        assert len(results) == 2
        assert all(isinstance(r, LayoutAnalysisResult) for r in results)
        assert results[0].page_num == 1
        assert results[1].page_num == 2

    def test_get_text_by_region_type(self):
        """Test text extraction by region type."""
        analyzer = LayoutAnalyzer()

        # Mock layout results
        results = [
            LayoutAnalysisResult(
                page_num=1,
                page_width=600,
                page_height=800,
                regions=[
                    LayoutRegion(
                        region_type=RegionType.TITLE,
                        bbox=(0, 0, 100, 20),
                        confidence=0.9,
                        page_num=1,
                        text_blocks=[TextBlock("Title 1", (0, 0, 100, 20), 1, 18.0, "Arial")],
                    ),
                    LayoutRegion(
                        region_type=RegionType.PARAGRAPH,
                        bbox=(0, 30, 100, 50),
                        confidence=0.8,
                        page_num=1,
                        text_blocks=[TextBlock("Para 1", (0, 30, 100, 50), 1, 12.0, "Arial")],
                    ),
                ],
            ),
        ]

        title_texts = analyzer.get_text_by_region_type(results, RegionType.TITLE)
        para_texts = analyzer.get_text_by_region_type(results, RegionType.PARAGRAPH)

        assert title_texts == {1: ["Title 1"]}
        assert para_texts == {1: ["Para 1"]}

    @patch("pdf_translator.layout_analyzer.layout_analyzer.logger")
    def test_analyze_page_layout_exception_handling(self, mock_logger):
        """Test exception handling in page layout analysis."""
        analyzer = LayoutAnalyzer()

        # Mock a scenario that causes an exception
        with patch.object(analyzer, "_analyze_layout_rules", side_effect=Exception("Test error")):
            page_info = PageInfo(
                page_num=1,
                width=600,
                height=800,
                text_blocks=[],
                raw_text="test",
            )

            results = analyzer.analyze_document_layout([page_info])

            # Should return fallback result
            assert len(results) == 1
            assert results[0].page_num == 1
            assert len(results[0].regions) == 0


class TestRegionType:
    """Test RegionType enum."""

    def test_region_type_values(self):
        """Test all region type values."""
        assert RegionType.TEXT.value == "text"
        assert RegionType.TITLE.value == "title"
        assert RegionType.PARAGRAPH.value == "paragraph"
        assert RegionType.LIST.value == "list"
        assert RegionType.TABLE.value == "table"
        assert RegionType.FIGURE.value == "figure"
        assert RegionType.HEADER.value == "header"
        assert RegionType.FOOTER.value == "footer"
        assert RegionType.COLUMN.value == "column"
        assert RegionType.SECTION.value == "section"


class TestLayoutRegion:
    """Test LayoutRegion dataclass."""

    def test_layout_region_creation(self):
        """Test layout region creation."""
        text_block = TextBlock("Test", (0, 0, 100, 20), 1, 12.0, "Arial")

        region = LayoutRegion(
            region_type=RegionType.PARAGRAPH,
            bbox=(0, 0, 100, 20),
            confidence=0.9,
            page_num=1,
            text_blocks=[text_block],
            column_index=0,
        )

        assert region.region_type == RegionType.PARAGRAPH
        assert region.bbox == (0, 0, 100, 20)
        assert region.confidence == 0.9
        assert region.page_num == 1
        assert len(region.text_blocks) == 1
        assert region.column_index == 0


class TestLayoutAnalysisResult:
    """Test LayoutAnalysisResult dataclass."""

    def test_layout_analysis_result_creation(self):
        """Test layout analysis result creation."""
        regions = [
            LayoutRegion(
                region_type=RegionType.TITLE,
                bbox=(0, 0, 100, 20),
                confidence=0.9,
                page_num=1,
                text_blocks=[],
            )
        ]

        result = LayoutAnalysisResult(
            page_num=1,
            page_width=600,
            page_height=800,
            regions=regions,
            column_count=2,
            has_tables=True,
            has_figures=False,
        )

        assert result.page_num == 1
        assert result.page_width == 600
        assert result.page_height == 800
        assert len(result.regions) == 1
        assert result.column_count == 2
        assert result.has_tables is True
        assert result.has_figures is False
