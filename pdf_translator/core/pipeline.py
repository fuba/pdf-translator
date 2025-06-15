"""Translation Pipeline - Main orchestration of PDF translation workflow.

This module coordinates all components to translate PDFs while preserving layout.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set

from pdf_translator.config.manager import ConfigManager
from pdf_translator.extractor import PDFExtractor
from pdf_translator.layout_analyzer import LayoutAnalyzer
from pdf_translator.models.document import Document
from pdf_translator.models.page import Page
from pdf_translator.post_processor import PostProcessor
from pdf_translator.renderer import DocumentRenderer
from pdf_translator.term_miner import TermMiner
from pdf_translator.translator import OllamaTranslator, OpenAITranslator
from pdf_translator.translator.chunked_translator import ChunkedTranslator


class TranslationPipeline:
    """Main pipeline for PDF translation."""

    def __init__(self, config: ConfigManager):
        """Initialize the translation pipeline."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.extractor = PDFExtractor(config)
        self.layout_analyzer = (
            LayoutAnalyzer(config) if config.get("layout_analysis", True) else None
        )
        self.term_miner = TermMiner(config) if config.get("term_extraction.enabled", True) else None
        # Create translator based on engine type
        engine = config.get("translation.engine", "ollama")
        use_chunked = config.get("translation.use_chunked", True)
        
        if use_chunked:
            # Use chunked translator for better performance and consistency
            self.translator = ChunkedTranslator(config)
        else:
            # Use traditional single-request translator
            if engine == "ollama":
                self.translator = OllamaTranslator(config)
            elif engine == "openai":
                self.translator = OpenAITranslator(config)
            else:
                raise ValueError(f"Unsupported translator engine: {engine}")
        
        self.post_processor = PostProcessor(config)
        self.renderer = DocumentRenderer(config)

        # Pipeline state
        self.technical_terms: Dict[str, str] = {}
        self.processed_terms: Set[str] = set()
        self.layout_results: Dict[int, Any] = {}  # Store layout results for rendering

    def analyze(self, input_path: str, pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """Analyze PDF without translation (dry run)."""
        self.logger.info(f"Analyzing PDF: {input_path}")
        start_time = time.time()

        # Extract pages
        document = self.extractor.extract(input_path, pages=pages)

        # Analyze layout for each page
        total_chars = 0
        text_pages = 0
        image_pages = 0
        all_terms = set()

        for page in document.pages:
            if page.has_text:
                text_pages += 1
                total_chars += sum(len(block.text) for block in page.text_blocks)
            else:
                image_pages += 1

            # Extract terms from this page
            if self.term_miner and page.has_text:
                page_text = "\n".join(block.text for block in page.text_blocks)
                terms_result = self.term_miner.extract_terms(page_text)
                if hasattr(terms_result, "terms") and terms_result.terms:
                    # Extract term keys if terms is a dict
                    if isinstance(terms_result.terms, dict):
                        all_terms.update(terms_result.terms.keys())
                    else:
                        # If terms is a list, just add the terms
                        all_terms.update(
                            term if isinstance(term, str) else term.text
                            for term in terms_result.terms
                        )

        processing_time = time.time() - start_time

        return {
            "total_pages": len(document.pages),
            "text_pages": text_pages,
            "image_pages": image_pages,
            "total_chars": total_chars,
            "terms": list(all_terms),
            "processing_time": processing_time,
            "metadata": document.metadata,
        }

    def translate(
        self, input_path: str, output_path: str, pages: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Translate PDF and save result."""
        self.logger.info(f"Starting translation: {input_path} -> {output_path}")
        start_time = time.time()

        # Step 1: Extract PDF content
        self.logger.info("Step 1: Extracting PDF content...")
        document = self.extractor.extract(input_path, pages=pages)

        # Step 2: Extract and lookup technical terms from entire document
        if self.term_miner:
            self.logger.info("Step 2: Extracting technical terms...")
            self._extract_document_terms(document)

        # Step 3: Process each page
        translated_pages = []
        total_pages = len(document.pages)
        
        for i, page in enumerate(document.pages):
            page_num = i + 1
            self.logger.info(f"🔄 Processing page {page_num}/{total_pages} ({(page_num/total_pages)*100:.1f}%)")
            
            # Add timeout protection per page
            page_start_time = time.time()
            
            try:
                translated_page = self._process_page(page, page_num)
                translated_pages.append(translated_page)
                
                page_duration = time.time() - page_start_time
                self.logger.info(f"✅ Page {page_num} completed in {page_duration:.1f}s")
                
            except Exception as e:
                page_duration = time.time() - page_start_time
                self.logger.error(f"❌ Page {page_num} failed after {page_duration:.1f}s: {str(e)}")
                # Add the original page as fallback
                translated_pages.append(page)

        # Step 4: Create translated document
        Document(
            pages=translated_pages,
            metadata={
                **document.metadata,
                "translated": True,
                "translation_engine": self.config.get("translation.engine"),
                "source_language": self.config.get("translation.source_language", "auto"),
                "target_language": self.config.get("translation.target_language", "ja"),
            },
        )

        # Step 5: Render output
        self.logger.info("Step 5: Rendering output...")

        # Prepare data for rendering
        page_infos = []
        translated_texts = {}
        layout_regions = {}

        for i, page in enumerate(document.pages):
            # Create PageInfo for original structure
            from pdf_translator.extractor.pdf_extractor import PageInfo
            from pdf_translator.extractor.pdf_extractor import TextBlock as ExtractorTextBlock

            text_blocks = []
            for block in page.text_blocks:
                text_blocks.append(
                    ExtractorTextBlock(
                        text=block.text,
                        bbox=(block.x, block.y, block.x + block.width, block.y + block.height),
                        page_num=page.number - 1,  # 0-based indexing
                        font_size=getattr(block, "font_size", 12.0),
                        font_name=getattr(block, "font_name", "Unknown"),
                    )
                )

            page_info = PageInfo(
                page_num=i,
                width=page.width,
                height=page.height,
                text_blocks=text_blocks,
                raw_text=page.text_content,
                has_images=page.has_images,
            )
            page_infos.append(page_info)

            # Get translated text for this page
            translated_page = translated_pages[i]
            translated_text = "\n\n".join(block.text for block in translated_page.text_blocks)
            translated_texts[i] = translated_text

            # Get layout regions if available
            if hasattr(self, "layout_results") and i in self.layout_results:
                layout_regions[i] = self.layout_results[i]

        # Render using the appropriate method
        self.renderer.render_from_pages(page_infos, translated_texts, output_path, layout_regions)

        # Calculate statistics
        processing_time = time.time() - start_time
        pages_processed = len(translated_pages)
        terms_extracted = len(self.technical_terms)

        self.logger.info(f"Translation completed in {processing_time:.1f}s")

        return {
            "processing_time": processing_time,
            "pages_processed": pages_processed,
            "terms_extracted": terms_extracted,
            "output_path": output_path,
        }

    def _extract_document_terms(self, document: Document) -> None:
        """Extract technical terms from entire document."""
        # Collect all text from document
        all_text = []
        for page in document.pages:
            if page.has_text:
                page_text = "\n".join(block.text for block in page.text_blocks)
                all_text.append(page_text)

        full_text = "\n".join(all_text)

        # Extract terms
        terms_result = self.term_miner.extract_terms(full_text)
        if hasattr(terms_result, "terms") and terms_result.terms:
            if isinstance(terms_result.terms, dict):
                self.technical_terms = terms_result.terms
            else:
                # Convert list to dict if needed
                self.technical_terms = {
                    term.text: term.translations.get("ja", term.text)
                    if hasattr(term, "translations")
                    else term.text
                    for term in terms_result.terms
                    if hasattr(term, "text")
                }
        else:
            self.technical_terms = {}

        self.logger.info(f"Extracted {len(self.technical_terms)} technical terms")

        # Log sample terms
        if self.technical_terms:
            sample_terms = list(self.technical_terms.items())[:5]
            for term, translation in sample_terms:
                self.logger.debug(f"  {term} -> {translation}")

    def _process_page(self, page: Page, page_number: int) -> Page:
        """Process a single page through the pipeline."""
        self.logger.info(f"Processing page {page_number}: has_text={page.has_text}, text_blocks={len(page.text_blocks)}")
        
        # Skip if no text (image-only page)
        if not page.has_text:
            self.logger.info(f"Page {page_number} is image-only, skipping translation")
            return page

        # Analyze layout if enabled
        if self.layout_analyzer:
            # Convert Page to PageInfo format for layout analyzer
            from pdf_translator.extractor.pdf_extractor import PageInfo
            from pdf_translator.extractor.pdf_extractor import TextBlock as ExtractorTextBlock

            # Convert text blocks
            extractor_blocks = []
            for block in page.text_blocks:
                extractor_block = ExtractorTextBlock(
                    text=block.text,
                    bbox=(block.x, block.y, block.x + block.width, block.y + block.height),
                    page_num=page.number - 1,  # PageInfo uses 0-based indexing
                    font_size=block.font_size or 12.0,
                    font_name=block.font_name or "Unknown",
                )
                extractor_blocks.append(extractor_block)

            # Create PageInfo
            page_info = PageInfo(
                page_num=page.number - 1,  # 0-based
                width=page.width,
                height=page.height,
                text_blocks=extractor_blocks,
                raw_text=page.text_content,
                has_images=page.has_images,
            )

            # Analyze layout
            layout_result = self.layout_analyzer.analyze_page_layout(page_info)

            # Store layout result for rendering
            self.layout_results[page.number - 1] = layout_result.regions

            # Update page regions based on layout analysis
            if layout_result.regions:
                from pdf_translator.models.layout import Region, RegionType

                page.regions = []
                self.logger.debug(f"Found {len(layout_result.regions)} layout regions")
                for layout_region in layout_result.regions:
                    # Map layout analyzer region type to model region type
                    region_type_mapping = {
                        "text": RegionType.PARAGRAPH,
                        "title": RegionType.TITLE,
                        "paragraph": RegionType.PARAGRAPH,
                        "list": RegionType.LIST,
                        "table": RegionType.TABLE,
                        "figure": RegionType.FIGURE,
                        "header": RegionType.HEADER,
                        "footer": RegionType.FOOTER,
                        "column": RegionType.PARAGRAPH,
                        "section": RegionType.PARAGRAPH,
                    }
                    region_type = region_type_mapping.get(
                        layout_region.region_type.value, RegionType.UNKNOWN
                    )
                    
                    self.logger.debug(f"Layout region: type={layout_region.region_type.value} -> {region_type}, bbox={layout_region.bbox}")

                    region = Region(
                        type=region_type,
                        x=layout_region.bbox[0],
                        y=layout_region.bbox[1],
                        width=layout_region.bbox[2] - layout_region.bbox[0],
                        height=layout_region.bbox[3] - layout_region.bbox[1],
                        confidence=layout_region.confidence,
                    )
                    page.add_region(region)

        # Translate text blocks
        translated_blocks = []
        
        self.logger.info(f"Starting translation for page {page_number} with {len(page.text_blocks)} text blocks")
        
        # Check if using chunked translator
        if isinstance(self.translator, ChunkedTranslator):
            self.logger.info(f"Using ChunkedTranslator for page {page_number}")
            # Process all blocks, maintaining original order
            text_block_map = {}  # Maps original block index to translated text
            page_text_blocks = []
            page_text = ""
            
            # First pass: collect text blocks and build page text
            for i, block in enumerate(page.text_blocks):
                if self._is_in_non_text_region(block, page):
                    self.logger.debug(f"Skipping block {i} in non-text region: {block.text[:50]}...")
                    continue
                page_text_blocks.append((i, block))  # Store original index
                page_text += block.text + "\n\n"
            
            self.logger.debug(f"Collected {len(page_text_blocks)} text blocks out of {len(page.text_blocks)} total blocks")
            
            if page_text.strip():
                # Translate entire page with chunked approach
                self.logger.info(f"Translating page {page_number} with chunked approach (length: {len(page_text)})")
                
                source_lang = self.config.get("translation.source_language", "auto")
                target_lang = self.config.get("translation.target_language", "ja")
                
                self.logger.debug(f"Source language: {source_lang}, Target language: {target_lang}")
                
                try:
                    translation_results = self.translator.translate_chunked(
                        page_text.strip(), source_lang, target_lang
                    )
                except Exception as e:
                    self.logger.error(f"Translation request failed: {e}")
                    # Return original page if translation fails
                    return page
                
                self.logger.debug(f"Translation results: {len(translation_results)} chunks")
                for i, result in enumerate(translation_results):
                    if result.success:
                        self.logger.debug(f"Chunk {i} translated successfully")
                    else:
                        self.logger.error(f"Chunk {i} translation failed: {result.error}")
                
                # Merge translation results
                merged_translation = self.translator.merge_translation_results(translation_results)
                self.logger.debug(f"Merged translation length: {len(merged_translation)}")
                
                # Split merged translation back to blocks (approximate)
                translated_paragraphs = [p.strip() for p in merged_translation.split('\n\n') if p.strip()]
                
                # Map translated paragraphs back to original blocks
                for j, (orig_idx, block) in enumerate(page_text_blocks):
                    if j < len(translated_paragraphs):
                        translated_text = translated_paragraphs[j]
                    else:
                        # Fallback: translate individually
                        result = self.translator.translate_chunk(
                            type('Chunk', (), {'text': block.text, 'chunk_id': j})(),
                            source_lang, target_lang
                        )
                        translated_text = result.translated_text if result.success else block.text
                    
                    # Post-process the translation
                    if self.post_processor:
                        result = self.post_processor.process(translated_text, self.technical_terms)
                        translated_text = (
                            result.processed_text if hasattr(result, "processed_text") else translated_text
                        )
                    
                    # Store mapping
                    text_block_map[orig_idx] = translated_text
            
            # Second pass: create translated blocks in original order
            for i, block in enumerate(page.text_blocks):
                if self._is_in_non_text_region(block, page):
                    # Add non-text blocks (figures, tables) as-is
                    translated_blocks.append(block)
                elif i in text_block_map:
                    # Add translated text block
                    translated_block = block.copy()
                    translated_block.text = text_block_map[i]
                    translated_blocks.append(translated_block)
                else:
                    # Should not happen, but add as-is for safety
                    translated_blocks.append(block)
        
        else:
            # Traditional block-by-block translation
            for block in page.text_blocks:
                # Skip if block is in a figure or table region
                if self._is_in_non_text_region(block, page):
                    translated_blocks.append(block)
                    continue

                # Translate the text
                self.logger.debug(f"Translating text block: {block.text[:50]}...")
                result = self.translator.translate(block.text)
                translated_text = (
                    result.translated_text if hasattr(result, "translated_text") else str(result)
                )
                self.logger.debug(f"Translation result: {translated_text[:50]}...")

                # Post-process the translation
                if self.post_processor:
                    result = self.post_processor.process(translated_text, self.technical_terms)
                    translated_text = (
                        result.processed_text if hasattr(result, "processed_text") else translated_text
                    )

                # Create translated block
                translated_block = block.copy()
                translated_block.text = translated_text
                translated_blocks.append(translated_block)

        # Create translated page
        translated_page = Page(
            number=page.number,
            width=page.width,
            height=page.height,
            text_blocks=translated_blocks,
            images=page.images,
            regions=page.regions,
        )

        return translated_page

    def _is_in_non_text_region(self, block: Any, page: Page) -> bool:
        """Check if text block is within a figure or table region."""
        if not page.regions:
            return False

        block_center_x = block.x + block.width / 2
        block_center_y = block.y + block.height / 2

        for region in page.regions:
            if region.type in ["figure", "table"]:
                if (
                    region.x <= block_center_x <= region.x + region.width
                    and region.y <= block_center_y <= region.y + region.height
                ):
                    return True

        return False
