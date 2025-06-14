"""Document rendering module for PDF translation output."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2
import markdown
from markupsafe import Markup

from src.extractor import PageInfo, TextBlock
from src.layout_analyzer import LayoutRegion, RegionType

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

    output_format: str = "markdown"  # markdown, html
    preserve_layout: bool = True  # Preserve original layout structure
    include_style: bool = True  # Include CSS styles for HTML
    page_breaks: bool = True  # Add page breaks between pages
    font_size_mapping: Dict[str, int] = None  # Map font sizes to heading levels
    
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

    def __init__(self, config: Optional[RenderConfig] = None):
        """Initialize document renderer.

        Args:
            config: Rendering configuration

        """
        self.config = config or RenderConfig()
        
        # Setup Jinja2 environment for HTML templates
        self.jinja_env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Create templates
        self._setup_templates()

    def _setup_templates(self):
        """Setup HTML templates."""
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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
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
        if self.config.output_format == "markdown":
            content = self._render_markdown(document, layout_regions)
        elif self.config.output_format == "html":
            content = self._render_html(document, layout_regions)
        else:
            raise ValueError(f"Unsupported output format: {self.config.output_format}")
        
        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        
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
        if hasattr(document, 'title') and document.title:
            lines.append(f"# {document.title}")
            lines.append("")
        
        # Process each page
        for page_num, page_text in document.annotated_pages.items():
            # Add page separator
            if self.config.page_breaks and page_num > 0:
                lines.append("---")
                lines.append("")
            
            lines.append(f"## Page {page_num + 1}")
            lines.append("")
            
            # If we have layout regions, use them for structure
            if layout_regions and page_num in layout_regions:
                self._render_regions_markdown(
                    lines, layout_regions[page_num], page_text
                )
            else:
                # Simple paragraph-based rendering
                paragraphs = page_text.strip().split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        lines.append(para.strip())
                        lines.append("")
        
        return '\n'.join(lines)

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
            region_text = "\n".join(block.text for block in region.text_blocks) if region.text_blocks else ""
            
            if region.region_type == RegionType.TITLE:
                lines.append(f"### {region_text}")
                lines.append("")
            elif region.region_type == RegionType.HEADER:
                lines.append(f"#### {region_text}")
                lines.append("")
            elif region.region_type == RegionType.LIST:
                # Format as list items
                items = region_text.split('\n')
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
            page_data = {
                'page_num': page_num,
                'blocks': [],
                'regions': []
            }
            
            if layout_regions and page_num in layout_regions:
                # Use layout regions
                for region in layout_regions[page_num]:
                    # Extract text from text blocks
                    region_text = "\n".join(block.text for block in region.text_blocks) if region.text_blocks else ""
                    
                    region_data = {
                        'type': region.region_type.value,
                        'blocks': [{
                            'type': self._get_block_type(region.region_type),
                            'text': self._escape_html(region_text)
                        }]
                    }
                    page_data['regions'].append(region_data)
            else:
                # Simple block-based rendering
                paragraphs = page_text.strip().split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        page_data['blocks'].append({
                            'type': 'paragraph',
                            'text': self._escape_html(para.strip())
                        })
            
            pages_data.append(page_data)
        
        # Render template
        # Get target language from config if available
        target_lang = 'en'
        if hasattr(document, 'config') and hasattr(document.config, 'target_lang'):
            target_lang = document.config.target_lang
        elif hasattr(document, 'config') and hasattr(document.config, 'target_language'):
            target_lang = document.config.target_language
        
        return self.html_template.render(
            title=getattr(document, 'title', 'Translated Document'),
            target_lang=target_lang,
            pages=pages_data,
            include_style=self.config.include_style,
            page_breaks=self.config.page_breaks,
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
        return Markup(text.replace('&', '&amp;')
                          .replace('<', '&lt;')
                          .replace('>', '&gt;')
                          .replace('"', '&quot;')
                          .replace("'", '&#39;'))

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