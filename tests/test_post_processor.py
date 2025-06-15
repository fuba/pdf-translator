"""Tests for post_processor module."""

from pdf_translator.post_processor import (
    PostProcessingResult,
    PostProcessor,
    PostProcessorConfig,
    TermAnnotation,
)
from pdf_translator.term_miner import Term


class TestPostProcessorConfig:
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "add_source_terms": True,
            "source_term_format": "訳語（原語）",
            "spacing_adjustment": True,
            "preserve_line_breaks": True,
            "min_term_length": 3,
        }
        config = PostProcessorConfig.from_dict(config_dict)

        assert config.add_source_terms is True
        assert config.source_term_format == "訳語（原語）"
        assert config.spacing_adjustment is True
        assert config.preserve_line_breaks is True
        assert config.min_term_length == 3

    def test_default_values(self):
        """Test default configuration values."""
        config = PostProcessorConfig()

        assert config.add_source_terms is True
        assert config.source_term_format == "{translation}（{original}）"
        assert config.spacing_adjustment is True
        assert config.preserve_line_breaks is True


class TestTermAnnotation:
    def test_annotation_creation(self):
        """Test TermAnnotation creation."""
        annotation = TermAnnotation(
            original_term="machine learning",
            translated_term="機械学習",
            position=10,
            first_occurrence=True,
        )

        assert annotation.original_term == "machine learning"
        assert annotation.translated_term == "機械学習"
        assert annotation.position == 10
        assert annotation.first_occurrence is True

    def test_format_annotation(self):
        """Test annotation formatting."""
        annotation = TermAnnotation(
            original_term="API", translated_term="API", position=0, first_occurrence=True
        )

        formatted = annotation.format_annotation("{translation}（{original}）")
        assert formatted == "API（API）"

        formatted_alt = annotation.format_annotation("{translation} [{original}]")
        assert formatted_alt == "API [API]"


class TestPostProcessor:
    def setup_method(self):
        """Set up for each test method."""
        self.config = PostProcessorConfig()
        self.processor = PostProcessor(self.config)

    def test_process_basic(self):
        """Test basic post-processing."""
        translated_text = "これは機械学習に関する文書です。"
        term_dict = {"machine learning": "機械学習"}

        result = self.processor.process(translated_text, term_dict)

        assert result.success is True
        assert result.processed_text is not None
        assert len(result.processed_text) > 0

    def test_add_source_term_annotations(self):
        """Test adding source term annotations."""
        translated_text = "機械学習は人工知能の一分野です。深層学習も重要な技術です。"
        terms = [
            Term("machine learning", 1, translations={"ja": "機械学習"}),
            Term("deep learning", 1, translations={"ja": "深層学習"}),
            Term("artificial intelligence", 1, translations={"ja": "人工知能"}),
        ]
        term_dict = {term.text: term.translations.get("ja", term.text) for term in terms}

        result = self.processor.process(translated_text, term_dict)

        # Should add source terms on first occurrence
        assert "機械学習（machine learning）" in result.processed_text
        assert "深層学習（deep learning）" in result.processed_text
        assert "人工知能（artificial intelligence）" in result.processed_text

    def test_first_occurrence_only(self):
        """Test that source terms are only added on first occurrence."""
        translated_text = "機械学習について説明します。機械学習は重要です。"
        term_dict = {"machine learning": "機械学習"}

        result = self.processor.process(translated_text, term_dict)

        # Count occurrences of the annotated term
        annotated_count = result.processed_text.count("機械学習（machine learning）")
        plain_count = result.processed_text.count("機械学習") - annotated_count

        assert annotated_count == 1  # Only first occurrence
        assert plain_count >= 1  # Other occurrences remain plain

    def test_preserve_line_breaks(self):
        """Test preserving line breaks."""
        translated_text = "第一段落です。\n\n第二段落です。\n第三段落です。"
        term_dict = {}

        result = self.processor.process(translated_text, term_dict)

        # Should preserve original line breaks
        assert "\n\n" in result.processed_text
        assert result.processed_text.count("\n") >= 3

    def test_spacing_adjustment(self):
        """Test spacing adjustment between Japanese and English."""
        config = PostProcessorConfig(spacing_adjustment=True)
        processor = PostProcessor(config)

        # Text with mixed Japanese and English without proper spacing
        translated_text = (
            "これはAPI（Application Programming Interface）の説明です。JSONファイルを使用します。"
        )
        term_dict = {}

        result = processor.process(translated_text, term_dict)

        # Should have proper spacing (this is a basic test)
        assert result.success is True

    def test_min_term_length_filter(self):
        """Test filtering terms by minimum length."""
        config = PostProcessorConfig(min_term_length=10)
        processor = PostProcessor(config)

        translated_text = "AIと機械学習について説明します。"
        term_dict = {
            "AI": "AI",  # 2 chars, too short when min_term_length=10
            "machine learning": "機械学習",  # 16 chars, long enough
        }

        result = processor.process(translated_text, term_dict)

        # AI should not be annotated (too short)
        assert "AI（AI）" not in result.processed_text
        # machine learning should be annotated
        assert "機械学習（machine learning）" in result.processed_text

    def test_case_insensitive_matching(self):
        """Test case-insensitive term matching."""
        translated_text = "機械学習とディープラーニングについて"
        term_dict = {"Machine Learning": "機械学習", "Deep Learning": "ディープラーニング"}

        result = self.processor.process(translated_text, term_dict)

        # Should match regardless of case in original term
        assert "機械学習（Machine Learning）" in result.processed_text
        assert "ディープラーニング（Deep Learning）" in result.processed_text

    def test_overlapping_terms(self):
        """Test handling overlapping terms."""
        translated_text = "自然言語処理システムについて"
        term_dict = {"natural language": "自然言語", "natural language processing": "自然言語処理"}

        result = self.processor.process(translated_text, term_dict)

        # Should prefer longer matches
        assert "自然言語処理（natural language processing）" in result.processed_text
        # Should not have overlapping annotations
        assert "自然言語（natural language）処理" not in result.processed_text

    def test_custom_format(self):
        """Test custom annotation format."""
        config = PostProcessorConfig(source_term_format="{translation} [{original}]")
        processor = PostProcessor(config)

        translated_text = "機械学習について"
        term_dict = {"machine learning": "機械学習"}

        result = processor.process(translated_text, term_dict)

        assert "機械学習 [machine learning]" in result.processed_text

    def test_no_source_terms(self):
        """Test processing without adding source terms."""
        config = PostProcessorConfig(add_source_terms=False)
        processor = PostProcessor(config)

        translated_text = "機械学習について説明します。"
        term_dict = {"machine learning": "機械学習"}

        result = processor.process(translated_text, term_dict)

        # Should not add source term annotations
        assert "機械学習（machine learning）" not in result.processed_text
        assert result.processed_text == translated_text  # Should be unchanged

    def test_process_with_terms_list(self):
        """Test processing with list of Term objects."""
        translated_text = "機械学習と人工知能について"
        terms = [
            Term("machine learning", 2, translations={"ja": "機械学習"}),
            Term("artificial intelligence", 1, translations={"ja": "人工知能"}),
        ]

        result = self.processor.process_with_terms(translated_text, terms)

        assert result.success is True
        assert "機械学習（machine learning）" in result.processed_text
        assert "人工知能（artificial intelligence）" in result.processed_text

    def test_error_handling(self):
        """Test error handling in post-processing."""
        # Test with None input
        result = self.processor.process(None, {})

        assert result.success is False
        assert result.error is not None

    def test_statistics(self):
        """Test post-processing statistics."""
        translated_text = "機械学習と深層学習について。機械学習は重要です。"
        term_dict = {"machine learning": "機械学習", "deep learning": "深層学習"}

        result = self.processor.process(translated_text, term_dict)

        assert result.success is True
        assert result.annotations_added >= 2  # At least 2 first occurrences
        assert result.terms_processed == 2  # 2 different terms


class TestPostProcessingResult:
    def test_result_creation(self):
        """Test PostProcessingResult creation."""
        result = PostProcessingResult(
            processed_text="処理済みテキスト", success=True, annotations_added=3, terms_processed=5
        )

        assert result.processed_text == "処理済みテキスト"
        assert result.success is True
        assert result.annotations_added == 3
        assert result.terms_processed == 5

    def test_failed_result(self):
        """Test failed processing result."""
        result = PostProcessingResult(processed_text="", success=False, error="Processing failed")

        assert result.success is False
        assert result.error == "Processing failed"
        assert result.processed_text == ""
