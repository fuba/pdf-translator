"""Document rendering module for PDF translation output."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jinja2
from markupsafe import Markup

from pdf_translator.config.manager import ConfigManager
from pdf_translator.extractor import PageInfo
from pdf_translator.layout_analyzer import LayoutRegion, RegionType

logger = logging.getLogger(__name__)


@dataclass
class AnnotatedDocument:
    """Document with translated and annotated text."""

    config: Any  # PostProcessorConfig or similar
    annotated_pages: Dict[int, str]  # Page number to annotated text
    title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderConfig:
    """Configuration for document rendering."""

    output_format: str = "markdown"  # markdown, html, pdf
    preserve_layout: bool = True  # Preserve original layout structure
    include_style: bool = True  # Include CSS styles for HTML
    page_breaks: bool = True  # Add page breaks between pages
    font_size_mapping: Dict[str, int] = None  # Map font sizes to heading levels
    pdf_page_size: str = "A4"  # PDF page size (A4, Letter, etc.)
    pdf_margin: float = 72  # PDF margins in points (72 = 1 inch)

    def __post_init__(self):
        """Initialize default font size mapping if not provided."""
        if self.font_size_mapping is None:
            self.font_size_mapping = {
                "title": 1,  # H1
                "heading": 2,  # H2
                "subheading": 3,  # H3
            }


class DocumentRenderer:
    """Render translated documents to various output formats."""

    def __init__(self, config: Optional[Union[ConfigManager, RenderConfig]] = None):
        """Initialize document renderer.

        Args:
            config: ConfigManager or RenderConfig instance

        """
        if isinstance(config, RenderConfig):
            self.render_config = config
            self.config = ConfigManager()
        else:
            self.config = config or ConfigManager()
            # Read output format from config
            output_format = self.config.get("output_format", "markdown")
            self.render_config = RenderConfig(output_format=output_format)

        # Setup Jinja2 environment for HTML templates
        self.jinja_env = jinja2.Environment(
            loader=jinja2.BaseLoader(), autoescape=jinja2.select_autoescape(["html", "xml"])
        )

        # Create templates
        self._setup_templates()

    def _setup_templates(self):
        """Set up HTML templates."""
        # Main HTML template
        self.html_template = self.jinja_env.from_string("""
<!DOCTYPE html>
<html lang="{{ target_lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    {% if include_style %}
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        .page {
            margin-bottom: 50px;
            padding: 20px;
            background: #fff;
            {% if page_breaks %}
            page-break-after: always;
            {% endif %}
        }
        .page-header {
            border-bottom: 2px solid #eee;
            margin-bottom: 20px;
            padding-bottom: 10px;
        }
        .page-number {
            color: #666;
            font-size: 0.9em;
        }
        .text-block {
            margin-bottom: 1em;
        }
        .text-block.title {
            font-size: 2em;
            font-weight: bold;
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        .text-block.heading {
            font-size: 1.5em;
            font-weight: bold;
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        .text-block.paragraph {
            text-align: justify;
        }
        .text-block.list {
            margin-left: 20px;
        }
        .text-block.table {
            background: #f9f9f9;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
        }
        .text-block.figure {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            background: #f5f5f5;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }
        .annotation {
            color: #666;
            font-size: 0.9em;
        }
        .region {
            margin-bottom: 1.5em;
            padding: 10px;
        }
        .region.column {
            border-left: 3px solid #e0e0e0;
            padding-left: 15px;
        }
        @media print {
            .page {
                page-break-after: always;
            }
        }
    </style>
    {% endif %}
</head>
<body>
    {% for page in pages %}
    <div class="page">
        <div class="page-header">
            <span class="page-number">Page {{ page.page_num + 1 }}</span>
        </div>
        <div class="page-content">
            {% if page.regions %}
                {% for region in page.regions %}
                <div class="region {{ region.type }}">
                    {% for block in region.blocks %}
                    <div class="text-block {{ block.type }}">
                        {{ block.text | safe }}
                    </div>
                    {% endfor %}
                </div>
                {% endfor %}
            {% else %}
                {% for block in page.blocks %}
                <div class="text-block {{ block.type }}">
                    {{ block.text | safe }}
                </div>
                {% endfor %}
            {% endif %}
        </div>
    </div>
    {% endfor %}
</body>
</html>
        """)

    def render(
        self,
        document: AnnotatedDocument,
        output_path: Path,
        layout_regions: Optional[Dict[int, List[LayoutRegion]]] = None,
    ) -> None:
        """Render annotated document to specified format.

        Args:
            document: Annotated document to render
            output_path: Output file path
            layout_regions: Optional layout regions for structure preservation

        """
        if self.render_config.output_format == "markdown":
            content = self._render_markdown(document, layout_regions)
            # Write text output
            from pathlib import Path
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        elif self.render_config.output_format == "html":
            content = self._render_html(document, layout_regions)
            # Write text output
            from pathlib import Path
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        elif self.render_config.output_format == "pdf":
            # Generate PDF directly
            self._render_pdf(document, output_path, layout_regions)
        else:
            raise ValueError(f"Unsupported output format: {self.render_config.output_format}")

        logger.info(f"Rendered document to {output_path}")

    def _render_markdown(
        self,
        document: AnnotatedDocument,
        layout_regions: Optional[Dict[int, List[LayoutRegion]]] = None,
    ) -> str:
        """Render document as Markdown.

        Args:
            document: Annotated document
            layout_regions: Optional layout regions

        Returns:
            Markdown content

        """
        lines = []

        # Add title if available
        if hasattr(document, "title") and document.title:
            lines.append(f"# {document.title}")
            lines.append("")

        # Process each page
        for page_num, page_text in document.annotated_pages.items():
            # Add page separator
            if self.render_config.page_breaks and page_num > 0:
                lines.append("---")
                lines.append("")

            lines.append(f"## Page {page_num + 1}")
            lines.append("")

            # If we have layout regions, use them for structure
            if layout_regions and page_num in layout_regions:
                self._render_regions_markdown(lines, layout_regions[page_num], page_text)
            else:
                # Simple paragraph-based rendering
                paragraphs = page_text.strip().split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        lines.append(para.strip())
                        lines.append("")

        return "\n".join(lines)

    def _render_regions_markdown(
        self,
        lines: List[str],
        regions: List[LayoutRegion],
        page_text: str,
    ) -> None:
        """Render layout regions as Markdown.

        Args:
            lines: Output lines list
            regions: Layout regions
            page_text: Full page text

        """
        # Group regions by type for better structure
        for region in regions:
            # Extract text from text blocks
            region_text = (
                "\n".join(block.text for block in region.text_blocks) if region.text_blocks else ""
            )

            if region.region_type == RegionType.TITLE:
                lines.append(f"### {region_text}")
                lines.append("")
            elif region.region_type == RegionType.HEADER:
                lines.append(f"#### {region_text}")
                lines.append("")
            elif region.region_type == RegionType.LIST:
                # Format as list items
                items = region_text.split("\n")
                for item in items:
                    if item.strip():
                        lines.append(f"- {item.strip()}")
                lines.append("")
            elif region.region_type == RegionType.TABLE:
                # Preserve table formatting
                lines.append("```")
                lines.append(region_text)
                lines.append("```")
                lines.append("")
            elif region.region_type == RegionType.FIGURE:
                # Mark as figure
                lines.append(f"**[Figure]** {region_text}")
                lines.append("")
            else:  # PARAGRAPH, TEXT, etc.
                lines.append(region_text)
                lines.append("")

    def _render_html(
        self,
        document: AnnotatedDocument,
        layout_regions: Optional[Dict[int, List[LayoutRegion]]] = None,
    ) -> str:
        """Render document as HTML.

        Args:
            document: Annotated document
            layout_regions: Optional layout regions

        Returns:
            HTML content

        """
        # Prepare page data
        pages_data = []

        for page_num, page_text in document.annotated_pages.items():
            page_data = {"page_num": page_num, "blocks": [], "regions": []}

            if layout_regions and page_num in layout_regions:
                # Use layout regions
                for region in layout_regions[page_num]:
                    # Extract text from text blocks
                    region_text = (
                        "\n".join(block.text for block in region.text_blocks)
                        if region.text_blocks
                        else ""
                    )

                    region_data = {
                        "type": region.region_type.value,
                        "blocks": [
                            {
                                "type": self._get_block_type(region.region_type),
                                "text": self._escape_html(region_text),
                            }
                        ],
                    }
                    page_data["regions"].append(region_data)
            else:
                # Simple block-based rendering
                paragraphs = page_text.strip().split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        page_data["blocks"].append(
                            {"type": "paragraph", "text": self._escape_html(para.strip())}
                        )

            pages_data.append(page_data)

        # Render template
        # Get target language from config if available
        target_lang = "en"
        if hasattr(document, "config") and hasattr(document.config, "target_lang"):
            target_lang = document.config.target_lang
        elif hasattr(document, "config") and hasattr(document.config, "target_language"):
            target_lang = document.config.target_language

        return self.html_template.render(
            title=getattr(document, "title", "Translated Document"),
            target_lang=target_lang,
            pages=pages_data,
            include_style=self.render_config.include_style,
            page_breaks=self.render_config.page_breaks,
        )

    def _get_block_type(self, region_type: RegionType) -> str:
        """Map region type to CSS class.

        Args:
            region_type: Region type

        Returns:
            CSS class name

        """
        mapping = {
            RegionType.TITLE: "title",
            RegionType.HEADER: "heading",
            RegionType.PARAGRAPH: "paragraph",
            RegionType.LIST: "list",
            RegionType.TABLE: "table",
            RegionType.FIGURE: "figure",
        }
        return mapping.get(region_type, "text")

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text

        """
        return Markup(
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def render_from_pages(
        self,
        pages: List[PageInfo],
        translated_texts: Dict[int, str],
        output_path: Path,
        layout_regions: Optional[Dict[int, List[LayoutRegion]]] = None,
    ) -> None:
        """Render from page info and translated texts.

        Args:
            pages: Original page information
            translated_texts: Translated text for each page
            output_path: Output file path
            layout_regions: Optional layout regions

        """

        # Create a simple annotated document
        class SimpleConfig:
            target_lang = "ja"

        document = AnnotatedDocument(config=SimpleConfig(), annotated_pages=translated_texts)

        self.render(document, output_path, layout_regions)

    def _render_pdf(
        self,
        document: AnnotatedDocument,
        output_path: Path,
        layout_regions: Optional[Dict[int, List[LayoutRegion]]] = None,
    ) -> None:
        """Render document as PDF with layout preservation.

        Args:
            document: Annotated document
            layout_regions: Optional layout regions
            output_path: Output PDF file path

        """
        try:
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
        except ImportError:
            raise ImportError("ReportLab is required for PDF output. Install with: pip install reportlab")

        # Create output directory
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup page size
        page_size = A4 if self.render_config.pdf_page_size == "A4" else letter
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            topMargin=self.render_config.pdf_margin,
            bottomMargin=self.render_config.pdf_margin,
            leftMargin=self.render_config.pdf_margin,
            rightMargin=self.render_config.pdf_margin,
        )

        # Setup styles
        styles = getSampleStyleSheet()
        
        # Japanese font support - try to register common Japanese fonts
        try:
            self._register_japanese_fonts()
        except Exception as e:
            logger.warning(f"Could not register Japanese fonts: {e}")

        # Create custom styles with Japanese font support
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=12,
            fontName='NotoSansCJK' if self._font_available('NotoSansCJK') else 'Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=6,
            fontName='NotoSansCJK' if self._font_available('NotoSansCJK') else 'Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='NotoSansCJK' if self._font_available('NotoSansCJK') else 'Helvetica'
        )

        # Build document content
        story = []
        
        # Add title if available
        if hasattr(document, 'title') and document.title:
            title_para = Paragraph(document.title, title_style)
            story.append(title_para)
            story.append(Spacer(1, 12))

        # Process each page
        for page_num, page_text in document.annotated_pages.items():
            # Add page header
            if self.render_config.page_breaks and page_num > 0:
                story.append(PageBreak())
            
            page_header = Paragraph(f"<b>Page {page_num + 1}</b>", heading_style)
            story.append(page_header)
            story.append(Spacer(1, 6))

            # If we have layout regions, use them for structure
            if layout_regions and page_num in layout_regions:
                self._add_regions_to_pdf_story(
                    story, layout_regions[page_num], page_text, 
                    title_style, heading_style, normal_style
                )
            else:
                # Simple paragraph-based rendering
                paragraphs = page_text.strip().split('\n\n')
                for para_text in paragraphs:
                    if para_text.strip():
                        # Clean up text for PDF
                        clean_text = self._clean_text_for_pdf(para_text.strip())
                        para = Paragraph(clean_text, normal_style)
                        story.append(para)
                        story.append(Spacer(1, 6))

        # Build PDF
        doc.build(story)
        logger.info(f"PDF generated successfully: {output_path}")

    def _register_japanese_fonts(self) -> None:
        """Register Japanese fonts for PDF rendering."""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os
        
        # Common paths for Japanese fonts on different systems
        font_paths = [
            # macOS
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial Unicode MS.ttf",
            # Linux (common locations)
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # Windows
            "C:/Windows/Fonts/msgothic.ttc",
            "C:/Windows/Fonts/msmincho.ttc",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # Register font with a simple name
                    if font_path.endswith('.ttc'):
                        # TrueType Collection requires subfont index
                        pdfmetrics.registerFont(TTFont('NotoSansCJK', font_path, subfontIndex=0))
                    else:
                        pdfmetrics.registerFont(TTFont('NotoSansCJK', font_path))
                    logger.info(f"Registered Japanese font: {font_path}")
                    return
                except Exception as e:
                    logger.debug(f"Failed to register font {font_path}: {e}")
                    continue
        
        logger.warning("No Japanese fonts found - using default fonts")

    def _font_available(self, font_name: str) -> bool:
        """Check if a font is available."""
        from reportlab.pdfbase import pdfmetrics
        try:
            pdfmetrics.getFont(font_name)
            return True
        except:
            return False

    def _add_regions_to_pdf_story(
        self,
        story: List,
        regions: List[LayoutRegion],
        page_text: str,
        title_style,
        heading_style,
        normal_style,
    ) -> None:
        """Add layout regions to PDF story."""
        from reportlab.platypus import Paragraph, Spacer
        
        for region in regions:
            # Extract text from text blocks
            region_text = (
                '\n'.join(block.text for block in region.text_blocks)
                if region.text_blocks else ''
            )
            
            if not region_text.strip():
                continue
                
            # Clean text for PDF
            clean_text = self._clean_text_for_pdf(region_text)
            
            if region.region_type == RegionType.TITLE:
                para = Paragraph(f"<b>{clean_text}</b>", title_style)
                story.append(para)
                story.append(Spacer(1, 12))
            elif region.region_type == RegionType.HEADER:
                para = Paragraph(f"<b>{clean_text}</b>", heading_style)
                story.append(para)
                story.append(Spacer(1, 8))
            elif region.region_type == RegionType.LIST:
                # Format as bullet points
                items = clean_text.split('\n')
                for item in items:
                    if item.strip():
                        bullet_text = f"• {item.strip()}"
                        para = Paragraph(bullet_text, normal_style)
                        story.append(para)
                story.append(Spacer(1, 6))
            elif region.region_type == RegionType.TABLE:
                # Preserve table formatting in monospace
                table_text = f"<font name='Courier'>{clean_text}</font>"
                para = Paragraph(table_text, normal_style)
                story.append(para)
                story.append(Spacer(1, 8))
            elif region.region_type == RegionType.FIGURE:
                # Mark as figure
                figure_text = f"<i>[Figure] {clean_text}</i>"
                para = Paragraph(figure_text, normal_style)
                story.append(para)
                story.append(Spacer(1, 8))
            else:  # PARAGRAPH, TEXT, etc.
                para = Paragraph(clean_text, normal_style)
                story.append(para)
                story.append(Spacer(1, 6))

    def _clean_text_for_pdf(self, text: str) -> str:
        """Clean text for PDF rendering."""
        # Escape XML/HTML characters for ReportLab
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Replace problematic characters
        text = text.replace('\u2019', "'")  # Right single quotation mark
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '--') # Em dash
        
        return text
