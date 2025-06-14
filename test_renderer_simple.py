#!/usr/bin/env python3
"""Simple demo for renderer functionality."""

import logging
from pathlib import Path

from src.post_processor import PostProcessorConfig
from src.renderer import AnnotatedDocument, DocumentRenderer, RenderConfig

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    """Test simple rendering."""
    # Create sample annotated document
    config = PostProcessorConfig()
    document = AnnotatedDocument(
        config=config,
        annotated_pages={
            0: "PDF翻訳システム\n\nこれは技術文書（technical document）の自動翻訳システムです。\n\n主な機能：\n- レイアウト保持\n- 専門用語抽出（term extraction）\n- 複数ページ対応",
            1: "システム構成\n\n以下のモジュールで構成されています：\n\n1. PDFExtractor - PDF解析\n2. LayoutAnalyzer - レイアウト解析\n3. TermMiner - 用語抽出\n4. Translator - 翻訳処理\n5. Renderer - 出力生成"
        },
        title="PDF Translation System Demo"
    )

    # Render to Markdown
    logger.info("Rendering to Markdown...")
    md_config = RenderConfig(output_format="markdown")
    md_renderer = DocumentRenderer(md_config)
    md_output = Path("output/simple_demo.md")
    md_renderer.render(document, md_output)
    logger.info(f"Saved to: {md_output}")

    # Show output
    if md_output.exists():
        content = md_output.read_text()
        logger.info("\nMarkdown output:")
        logger.info("-" * 60)
        logger.info(content)

    # Render to HTML
    logger.info("\nRendering to HTML...")
    html_config = RenderConfig(output_format="html")
    html_renderer = DocumentRenderer(html_config)
    html_output = Path("output/simple_demo.html")
    html_renderer.render(document, html_output)
    logger.info(f"Saved to: {html_output}")

    logger.info("\nDemo completed!")


if __name__ == "__main__":
    main()
