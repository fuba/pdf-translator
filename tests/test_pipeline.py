"""Tests for the translation pipeline integration."""

from unittest.mock import Mock, patch

import pytest

from pdf_translator.config.manager import ConfigManager
from pdf_translator.core.pipeline import TranslationPipeline
from pdf_translator.models.document import Document
from pdf_translator.models.page import Page, TextBlock


class TestTranslationPipeline:
    """Test cases for TranslationPipeline."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            "layout.enabled": True,
            "term_extraction.enabled": True,
            "translation.engine": "ollama",
            "translation.source_language": "en",
            "translation.target_language": "ja",
            "output.format": "html",
            "extraction.max_pages": 50,
            "extraction.enable_ocr": True
        }.get(key, default)
        return config

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        # Create text blocks
        text_blocks = [
            TextBlock(
                text="This is a test document.",
                x=100,
                y=100,
                width=200,
                height=20,
                font_size=12,
                font_name="Arial"
            ),
            TextBlock(
                text="Machine learning is important.",
                x=100,
                y=150,
                width=250,
                height=20,
                font_size=12,
                font_name="Arial"
            )
        ]

        # Create page
        page = Page(
            number=1,
            width=595,
            height=842,
            text_blocks=text_blocks
        )

        # Create document
        return Document(
            pages=[page],
            metadata={"source": "test.pdf"}
        )

    def test_pipeline_initialization(self, mock_config):
        """Test pipeline initialization."""
        pipeline = TranslationPipeline(mock_config)

        assert pipeline.config == mock_config
        assert pipeline.extractor is not None
        assert pipeline.layout_analyzer is not None
        assert pipeline.term_miner is not None
        assert pipeline.translator is not None
        assert pipeline.post_processor is not None
        assert pipeline.renderer is not None

    def test_pipeline_initialization_with_disabled_components(self):
        """Test pipeline initialization with disabled components."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            "layout.enabled": False,
            "term_extraction.enabled": False,
            "translation.engine": "ollama"
        }.get(key, default)

        pipeline = TranslationPipeline(config)

        assert pipeline.layout_analyzer is None
        assert pipeline.term_miner is None

    @patch('pdf_translator.core.pipeline.PDFExtractor')
    def test_analyze_method(self, mock_extractor_class, mock_config, sample_document):
        """Test the analyze method."""
        # Setup mock extractor
        mock_extractor = Mock()
        mock_extractor.extract.return_value = sample_document
        mock_extractor_class.return_value = mock_extractor

        # Mock term miner
        with patch('pdf_translator.core.pipeline.TermMiner') as mock_term_miner_class:
            mock_term_miner = Mock()
            # Return object with terms attribute
            mock_result = Mock()
            mock_result.terms = {
                "machine learning": "機械学習",
                "document": "文書"
            }
            mock_term_miner.extract_terms.return_value = mock_result
            mock_term_miner_class.return_value = mock_term_miner

            pipeline = TranslationPipeline(mock_config)
            result = pipeline.analyze("test.pdf")

        # Verify results
        assert result["total_pages"] == 1
        assert result["text_pages"] == 1
        assert result["image_pages"] == 0
        assert result["total_chars"] > 0
        assert "machine learning" in result["terms"]
        assert "document" in result["terms"]
        assert "processing_time" in result
        assert "metadata" in result

    @patch('pdf_translator.core.pipeline.PDFExtractor')
    @patch('pdf_translator.core.pipeline.TermMiner')
    @patch('pdf_translator.core.pipeline.OllamaTranslator')
    @patch('pdf_translator.core.pipeline.PostProcessor')
    @patch('pdf_translator.core.pipeline.DocumentRenderer')
    def test_translate_method(self, mock_renderer_class, mock_post_processor_class,
                             mock_translator_class, mock_term_miner_class,
                             mock_extractor_class, mock_config, sample_document):
        """Test the translate method."""
        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract.return_value = sample_document
        mock_extractor_class.return_value = mock_extractor

        mock_term_miner = Mock()
        # Return object with terms attribute
        mock_result = Mock()
        mock_result.terms = {
            "machine learning": "機械学習",
            "document": "文書"
        }
        mock_term_miner.extract_terms.return_value = mock_result
        mock_term_miner_class.return_value = mock_term_miner

        mock_translator = Mock()
        mock_translator.translate.side_effect = [
            "これはテスト文書です。",
            "機械学習は重要です。"
        ]
        mock_translator_class.return_value = mock_translator

        mock_post_processor = Mock()
        mock_post_processor.process.side_effect = lambda text, terms, processed: f"[処理済み] {text}"
        mock_post_processor_class.return_value = mock_post_processor

        mock_renderer = Mock()
        mock_renderer_class.return_value = mock_renderer

        # Test translation
        pipeline = TranslationPipeline(mock_config)
        result = pipeline.translate("test.pdf", "output.html")

        # Verify results
        assert result["processing_time"] >= 0
        assert result["pages_processed"] == 1
        assert result["terms_extracted"] == 2
        assert result["output_path"] == "output.html"

        # Verify method calls
        mock_extractor.extract.assert_called_once_with("test.pdf", pages=None)
        mock_term_miner.extract_terms.assert_called()
        mock_translator.translate.assert_called()
        mock_post_processor.process.assert_called()
        mock_renderer.render.assert_called_once()

    @patch('pdf_translator.core.pipeline.PDFExtractor')
    def test_translate_with_page_filter(self, mock_extractor_class, mock_config, sample_document):
        """Test translation with specific page numbers."""
        mock_extractor = Mock()
        mock_extractor.extract.return_value = sample_document
        mock_extractor_class.return_value = mock_extractor

        # Setup mocked TermMiner
        mock_term_miner = Mock()
        mock_result = Mock()
        mock_result.terms = {}  # Empty terms for this test
        mock_term_miner.extract_terms.return_value = mock_result

        with patch.multiple(
            'pdf_translator.core.pipeline',
            TermMiner=Mock(return_value=mock_term_miner),
            OllamaTranslator=Mock(),
            PostProcessor=Mock(),
            DocumentRenderer=Mock()
        ):
            pipeline = TranslationPipeline(mock_config)
            pipeline.translate("test.pdf", "output.html", pages=[1, 2, 3])

        mock_extractor.extract.assert_called_once_with("test.pdf", pages=[1, 2, 3])

    def test_process_page_with_image_only(self, mock_config):
        """Test processing of image-only page."""
        # Create image-only page
        page = Page(
            number=1,
            width=595,
            height=842,
            text_blocks=[],  # No text blocks
            images=[]
        )

        pipeline = TranslationPipeline(mock_config)
        result = pipeline._process_page(page, 1)

        # Should return the same page unchanged
        assert result == page

    def test_is_in_non_text_region(self, mock_config):
        """Test detection of non-text regions."""
        from pdf_translator.models.layout import Region

        # Create a text block
        text_block = Mock()
        text_block.x = 100
        text_block.y = 100
        text_block.width = 200
        text_block.height = 20

        # Create page with figure region
        page = Page(
            number=1,
            width=595,
            height=842,
            text_blocks=[],
            regions=[
                Region(
                    type="figure",
                    x=90,
                    y=90,
                    width=220,
                    height=40
                )
            ]
        )

        pipeline = TranslationPipeline(mock_config)
        result = pipeline._is_in_non_text_region(text_block, page)

        assert result is True

    def test_extract_document_terms(self, mock_config, sample_document):
        """Test technical term extraction from document."""
        with patch('pdf_translator.core.pipeline.TermMiner') as mock_term_miner_class:
            mock_term_miner = Mock()
            # Return object with terms attribute
            mock_result = Mock()
            mock_result.terms = {
                "machine learning": "機械学習",
                "document": "文書"
            }
            mock_term_miner.extract_terms.return_value = mock_result
            mock_term_miner_class.return_value = mock_term_miner

            pipeline = TranslationPipeline(mock_config)
            pipeline._extract_document_terms(sample_document)

        assert len(pipeline.technical_terms) == 2
        assert pipeline.technical_terms["machine learning"] == "機械学習"
        assert pipeline.technical_terms["document"] == "文書"
