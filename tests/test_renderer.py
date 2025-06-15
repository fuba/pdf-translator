"""Tests for document rendering functionality."""

import pytest

from pdf_translator.extractor import PageInfo, TextBlock
from pdf_translator.layout_analyzer import LayoutRegion, RegionType
from pdf_translator.post_processor import PostProcessorConfig
from pdf_translator.renderer import AnnotatedDocument, DocumentRenderer, RenderConfig


class TestRenderConfig:
    """Test render configuration."""

    def test_default_config(self):
        """Test default render configuration."""
        config = RenderConfig()
        assert config.output_format == "markdown"
        assert config.preserve_layout is True
        assert config.include_style is True
        assert config.page_breaks is True
        assert config.font_size_mapping == {
            "title": 1,
            "heading": 2,
            "subheading": 3,
        }

    def test_custom_config(self):
        """Test custom render configuration."""
        config = RenderConfig(
            output_format="html",
            preserve_layout=False,
            page_breaks=False,
        )
        assert config.output_format == "html"
        assert config.preserve_layout is False
        assert config.page_breaks is False


class TestDocumentRenderer:
    """Test document renderer functionality."""

    @pytest.fixture
    def renderer(self):
        """Create renderer instance."""
        return DocumentRenderer()

    @pytest.fixture
    def sample_document(self):
        """Create sample annotated document."""
        config = PostProcessorConfig()
        return AnnotatedDocument(
            config=config,
            annotated_pages={
                0: "これはタイトルです\n\nこれは段落です。専門用語（technical term）が含まれています。\n\nもう一つの段落です。",
                1: "2ページ目のタイトル\n\nこれは2ページ目の内容です。\n\n- リスト項目1\n- リスト項目2\n- リスト項目3",
            },
        )

    @pytest.fixture
    def layout_regions(self):
        """Create sample layout regions."""
        return {
            0: [
                LayoutRegion(
                    region_type=RegionType.TITLE,
                    bbox=(0, 0, 100, 50),
                    confidence=0.95,
                    page_num=0,
                    text_blocks=[
                        TextBlock("これはタイトルです", (0, 0, 100, 50), 0, 18, "Arial", "title")
                    ],
                ),
                LayoutRegion(
                    region_type=RegionType.PARAGRAPH,
                    bbox=(0, 60, 100, 150),
                    confidence=0.9,
                    page_num=0,
                    text_blocks=[
                        TextBlock(
                            "これは段落です。専門用語（technical term）が含まれています。",
                            (0, 60, 100, 150),
                            0,
                            12,
                            "Arial",
                            "paragraph",
                        )
                    ],
                ),
                LayoutRegion(
                    region_type=RegionType.PARAGRAPH,
                    bbox=(0, 160, 100, 200),
                    confidence=0.9,
                    page_num=0,
                    text_blocks=[
                        TextBlock(
                            "もう一つの段落です。", (0, 160, 100, 200), 0, 12, "Arial", "paragraph"
                        )
                    ],
                ),
            ],
            1: [
                LayoutRegion(
                    region_type=RegionType.HEADER,
                    bbox=(0, 0, 100, 40),
                    confidence=0.95,
                    page_num=1,
                    text_blocks=[
                        TextBlock("2ページ目のタイトル", (0, 0, 100, 40), 1, 16, "Arial", "heading")
                    ],
                ),
                LayoutRegion(
                    region_type=RegionType.PARAGRAPH,
                    bbox=(0, 50, 100, 100),
                    confidence=0.9,
                    page_num=1,
                    text_blocks=[
                        TextBlock(
                            "これは2ページ目の内容です。",
                            (0, 50, 100, 100),
                            1,
                            12,
                            "Arial",
                            "paragraph",
                        )
                    ],
                ),
                LayoutRegion(
                    region_type=RegionType.LIST,
                    bbox=(0, 110, 100, 200),
                    confidence=0.85,
                    page_num=1,
                    text_blocks=[
                        TextBlock("リスト項目1", (0, 110, 100, 130), 1, 12, "Arial", "list"),
                        TextBlock("リスト項目2", (0, 140, 100, 160), 1, 12, "Arial", "list"),
                        TextBlock("リスト項目3", (0, 170, 100, 190), 1, 12, "Arial", "list"),
                    ],
                ),
            ],
        }

    def test_init_default(self, renderer):
        """Test renderer initialization with defaults."""
        assert renderer.config.output_format == "markdown"
        assert renderer.jinja_env is not None
        assert renderer.html_template is not None

    def test_init_custom_config(self):
        """Test renderer initialization with custom config."""
        config = RenderConfig(output_format="html")
        renderer = DocumentRenderer(config)
        assert renderer.config.output_format == "html"

    def test_render_markdown(self, renderer, sample_document, tmp_path):
        """Test Markdown rendering."""
        output_path = tmp_path / "output.md"
        renderer.render(sample_document, output_path)

        assert output_path.exists()
        content = output_path.read_text()

        # Check content
        assert "## Page 1" in content
        assert "## Page 2" in content
        assert "これはタイトルです" in content
        assert "専門用語（technical term）" in content
        assert "2ページ目のタイトル" in content

    def test_render_markdown_with_layout(self, renderer, sample_document, layout_regions, tmp_path):
        """Test Markdown rendering with layout regions."""
        output_path = tmp_path / "output_layout.md"
        renderer.render(sample_document, output_path, layout_regions)

        assert output_path.exists()
        content = output_path.read_text()

        # Check structure
        assert "### これはタイトルです" in content  # Title as H3
        assert "#### 2ページ目のタイトル" in content  # Heading as H4
        assert "- リスト項目1" in content  # List formatting
        assert "- リスト項目2" in content
        assert "- リスト項目3" in content

    def test_render_html(self, tmp_path):
        """Test HTML rendering."""
        config = RenderConfig(output_format="html")
        renderer = DocumentRenderer(config)

        document = AnnotatedDocument(
            config=PostProcessorConfig(),
            annotated_pages={
                0: "Title\n\nParagraph with content.",
            },
        )

        output_path = tmp_path / "output.html"
        renderer.render(document, output_path)

        assert output_path.exists()
        content = output_path.read_text()

        # Check HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content
        assert "<style>" in content  # Default includes style
        assert "Page 1" in content
        assert "Title" in content
        assert "Paragraph with content." in content

    def test_render_html_without_style(self, tmp_path):
        """Test HTML rendering without style."""
        config = RenderConfig(output_format="html", include_style=False)
        renderer = DocumentRenderer(config)

        document = AnnotatedDocument(config=PostProcessorConfig(), annotated_pages={0: "Content"})

        output_path = tmp_path / "output_no_style.html"
        renderer.render(document, output_path)

        content = output_path.read_text()
        assert "<style>" not in content

    def test_render_unsupported_format(self, renderer, sample_document, tmp_path):
        """Test rendering with unsupported format."""
        renderer.config.output_format = "pdf"
        output_path = tmp_path / "output.pdf"

        with pytest.raises(ValueError, match="Unsupported output format"):
            renderer.render(sample_document, output_path)

    def test_render_from_pages(self, renderer, tmp_path):
        """Test rendering from page info."""
        pages = [
            PageInfo(
                page_num=0,
                width=595,
                height=842,
                text_blocks=[
                    TextBlock("Title", (0, 0, 100, 50), 0, 18, "Arial", "title"),
                    TextBlock("Content", (0, 60, 100, 100), 0, 12, "Arial", "paragraph"),
                ],
                raw_text="Title\nContent",
            )
        ]

        translated_texts = {0: "タイトル\n\n内容です。"}

        output_path = tmp_path / "from_pages.md"
        renderer.render_from_pages(pages, translated_texts, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "タイトル" in content
        assert "内容です。" in content

    def test_escape_html(self, renderer):
        """Test HTML escaping."""
        text = "Test <tag> & \"quotes\" 'apostrophe'"
        escaped = renderer._escape_html(text)

        assert "&lt;" in str(escaped)
        assert "&gt;" in str(escaped)
        assert "&amp;" in str(escaped)
        assert "&quot;" in str(escaped)
        assert "&#39;" in str(escaped)

    def test_get_block_type(self, renderer):
        """Test block type mapping."""
        assert renderer._get_block_type(RegionType.TITLE) == "title"
        assert renderer._get_block_type(RegionType.HEADER) == "heading"
        assert renderer._get_block_type(RegionType.PARAGRAPH) == "paragraph"
        assert renderer._get_block_type(RegionType.LIST) == "list"
        assert renderer._get_block_type(RegionType.TABLE) == "table"
        assert renderer._get_block_type(RegionType.FIGURE) == "figure"

    def test_render_with_page_breaks(self, renderer, sample_document, tmp_path):
        """Test rendering with page breaks."""
        output_path = tmp_path / "with_breaks.md"
        renderer.render(sample_document, output_path)

        content = output_path.read_text()
        assert "---" in content  # Markdown page break

    def test_render_without_page_breaks(self, sample_document, tmp_path):
        """Test rendering without page breaks."""
        config = RenderConfig(page_breaks=False)
        renderer = DocumentRenderer(config)

        output_path = tmp_path / "no_breaks.md"
        renderer.render(sample_document, output_path)

        content = output_path.read_text()
        assert "---" not in content

    def test_render_table_region(self, renderer, tmp_path):
        """Test rendering table regions."""
        regions = {
            0: [
                LayoutRegion(
                    region_type=RegionType.TABLE,
                    bbox=(0, 0, 100, 100),
                    confidence=0.9,
                    page_num=0,
                    text_blocks=[
                        TextBlock(
                            "Column1\tColumn2\nData1\tData2\nData3\tData4",
                            (0, 0, 100, 100),
                            0,
                            12,
                            "Arial",
                            "table",
                        )
                    ],
                ),
            ]
        }

        document = AnnotatedDocument(
            config=PostProcessorConfig(), annotated_pages={0: "Table content"}
        )

        output_path = tmp_path / "table.md"
        renderer.render(document, output_path, regions)

        content = output_path.read_text()
        assert "```" in content  # Code block for table
        assert "Column1\tColumn2" in content

    def test_render_figure_region(self, renderer, tmp_path):
        """Test rendering figure regions."""
        regions = {
            0: [
                LayoutRegion(
                    region_type=RegionType.FIGURE,
                    bbox=(0, 0, 100, 100),
                    confidence=0.9,
                    page_num=0,
                    text_blocks=[
                        TextBlock(
                            "Figure 1: Sample diagram", (0, 0, 100, 100), 0, 12, "Arial", "figure"
                        )
                    ],
                ),
            ]
        }

        document = AnnotatedDocument(
            config=PostProcessorConfig(), annotated_pages={0: "Figure content"}
        )

        output_path = tmp_path / "figure.md"
        renderer.render(document, output_path, regions)

        content = output_path.read_text()
        assert "**[Figure]**" in content
        assert "Figure 1: Sample diagram" in content

    def test_create_output_directory(self, renderer, sample_document, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_path = tmp_path / "nested" / "dir" / "output.md"
        renderer.render(sample_document, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()
