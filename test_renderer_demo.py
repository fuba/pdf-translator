#!/usr/bin/env python3
"""Demo script to test rendering functionality."""

import logging
from pathlib import Path

from src.extractor import PDFExtractor
from src.layout_analyzer import LayoutAnalyzer
from src.post_processor import PostProcessor, PostProcessorConfig
from src.renderer import AnnotatedDocument, DocumentRenderer, RenderConfig
from src.term_miner import TermMiner, TermMinerConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_rendering_pipeline():
    """Test complete rendering pipeline."""
    # Test file
    pdf_path = Path("tests/fixtures/sample_english.pdf")
    if not pdf_path.exists():
        logger.error(f"Test file not found: {pdf_path}")
        return

    logger.info("=" * 60)
    logger.info("Testing PDF Translation and Rendering Pipeline")
    logger.info("=" * 60)

    try:
        # 1. Extract PDF
        logger.info("\n1. Extracting PDF...")
        extractor = PDFExtractor(use_ocr=False)
        pages = extractor.extract_pdf(pdf_path)
        logger.info(f"   Extracted {len(pages)} pages")

        # 2. Analyze layout
        logger.info("\n2. Analyzing layout...")
        analyzer = LayoutAnalyzer()
        layout_results = {}
        for page in pages:
            result = analyzer.analyze_page_layout(page)
            layout_results[page.page_num] = result.regions
            logger.info(f"   Page {page.page_num + 1}: {len(result.regions)} regions detected")

        # 3. Extract terms
        logger.info("\n3. Extracting technical terms...")
        term_config = TermMinerConfig()
        term_miner = TermMiner(term_config)
        all_terms = {}
        for page in pages:
            result = term_miner.extract_terms(page.raw_text)
            if result.success:
                for term in result.terms:
                    if term.translations and 'ja' in term.translations:
                        all_terms[term.text] = term.translations['ja']
        logger.info(f"   Found {len(all_terms)} terms with translations")

        # 4. Translate (mock for demo)
        logger.info("\n4. Simulating translation...")
        translated_pages = {}
        for page in pages:
            # Simple mock translation
            translated_text = page.raw_text.replace(
                "Technical Document", "技術文書"
            ).replace(
                "Introduction", "はじめに"
            ).replace(
                "This document", "この文書"
            ).replace(
                "technical", "技術的な"
            )
            translated_pages[page.page_num] = translated_text

        # 5. Post-process
        logger.info("\n5. Post-processing translations...")
        post_config = PostProcessorConfig(
            add_source_terms=True,
            source_term_format="{translation}（{original}）"
        )
        post_processor = PostProcessor(post_config)

        annotated_pages = {}
        for page_num, text in translated_pages.items():
            result = post_processor.process(text, all_terms)
            annotated_pages[page_num] = result.processed_text
            logger.info(f"   Page {page_num + 1}: {result.annotations_added} annotations added")

        # 6. Create annotated document
        document = AnnotatedDocument(
            config=post_config,
            annotated_pages=annotated_pages,
            title="Technical Document Translation Demo"
        )

        # 7. Render to Markdown
        logger.info("\n6. Rendering to Markdown...")
        md_config = RenderConfig(output_format="markdown")
        md_renderer = DocumentRenderer(md_config)
        md_output = Path("output/demo_output.md")
        md_renderer.render(document, md_output, layout_results)
        logger.info(f"   Saved to: {md_output}")

        # Show sample output
        if md_output.exists():
            content = md_output.read_text()
            logger.info("\n   Sample output (first 500 chars):")
            logger.info("   " + "-" * 50)
            sample = content[:500].replace("\n", "\n   ")
            logger.info(f"   {sample}...")

        # 8. Render to HTML
        logger.info("\n7. Rendering to HTML...")
        html_config = RenderConfig(output_format="html", include_style=True)
        html_renderer = DocumentRenderer(html_config)
        html_output = Path("output/demo_output.html")
        html_renderer.render(document, html_output, layout_results)
        logger.info(f"   Saved to: {html_output}")

        logger.info("\n" + "=" * 60)
        logger.info("Rendering demo completed successfully!")
        logger.info("Check the output directory for generated files.")

    except Exception as e:
        logger.error(f"Error in rendering pipeline: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_rendering_pipeline()
