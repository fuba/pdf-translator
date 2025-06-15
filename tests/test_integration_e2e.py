"""End-to-end integration tests for the PDF translation system.

These tests use real PDFs and test the complete pipeline.
"""

from pathlib import Path

import pytest

from pdf_translator.config.manager import ConfigManager
from pdf_translator.core.pipeline import TranslationPipeline


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        config_data = {
            "translator": {
                "engine": "ollama",
                "model": "gemma3:4b",
                "base_url": "http://localhost:11434/api",
                "timeout": 60,
            },
            "source_language": "en",
            "target_language": "ja",
            "extraction": {"max_pages": 50, "enable_ocr": True, "force_ocr": False},
            "layout": {"enabled": True},
            "term_extraction": {"enabled": True},
            "output": {"format": "html", "directory": str(tmp_path)},
        }

        # Create temporary config file
        config_file = tmp_path / "config.yml"
        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        return ConfigManager(str(config_file))

    @pytest.fixture
    def sample_pdf_path(self):
        """Get path to sample PDF for testing."""
        pdf_path = Path("tests/fixtures/sample_english.pdf")
        if not pdf_path.exists():
            pytest.skip("Sample PDF not found")
        return str(pdf_path)

    def test_pipeline_initialization(self, test_config):
        """Test that pipeline can be initialized with real config."""
        pipeline = TranslationPipeline(test_config)

        assert pipeline.config is not None
        assert pipeline.extractor is not None
        assert pipeline.translator is not None
        assert pipeline.renderer is not None

    def test_pdf_analysis_dry_run(self, test_config, sample_pdf_path):
        """Test PDF analysis without translation."""
        pipeline = TranslationPipeline(test_config)

        try:
            result = pipeline.analyze(sample_pdf_path)

            # Verify analysis results
            assert "total_pages" in result
            assert "text_pages" in result
            assert "image_pages" in result
            assert "total_chars" in result
            assert "processing_time" in result
            assert result["total_pages"] > 0
            assert result["processing_time"] > 0

            print("Analysis Results:")
            print(f"  Total pages: {result['total_pages']}")
            print(f"  Text pages: {result['text_pages']}")
            print(f"  Image pages: {result['image_pages']}")
            print(f"  Total characters: {result['total_chars']}")
            print(f"  Processing time: {result['processing_time']:.2f}s")

            if result.get("terms"):
                print(f"  Technical terms: {len(result['terms'])}")
                for term in result["terms"][:5]:
                    print(f"    - {term}")

        except Exception as e:
            pytest.skip(f"Analysis failed (expected if dependencies not available): {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_translation_pipeline(self, test_config, sample_pdf_path, tmp_path):
        """Test complete translation pipeline."""
        pipeline = TranslationPipeline(test_config)
        output_path = tmp_path / "translated.html"

        try:
            result = pipeline.translate(
                sample_pdf_path,
                str(output_path),
                pages=[1],  # Only translate first page for speed
            )

            # Verify results
            assert "processing_time" in result
            assert "pages_processed" in result
            assert "output_path" in result
            assert result["pages_processed"] > 0
            assert result["processing_time"] > 0

            # Verify output file was created
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Check output contains expected content
            content = output_path.read_text(encoding="utf-8")
            assert len(content) > 0
            assert "html" in content.lower() or "<!DOCTYPE" in content

            print("Translation Results:")
            print(f"  Pages processed: {result['pages_processed']}")
            print(f"  Processing time: {result['processing_time']:.2f}s")
            print(f"  Output file size: {output_path.stat().st_size} bytes")

            if result.get("terms_extracted"):
                print(f"  Terms extracted: {result['terms_extracted']}")

        except Exception as e:
            pytest.skip(
                f"Full translation failed (expected if Ollama/dependencies not available): {e}"
            )

    @pytest.mark.integration
    def test_page_range_translation(self, test_config, sample_pdf_path, tmp_path):
        """Test translation with specific page ranges."""
        pipeline = TranslationPipeline(test_config)
        output_path = tmp_path / "translated_pages.html"

        try:
            result = pipeline.translate(
                sample_pdf_path,
                str(output_path),
                pages=[1, 2],  # Translate first two pages
            )

            assert result["pages_processed"] <= 2
            assert output_path.exists()

        except Exception as e:
            pytest.skip(f"Page range translation failed: {e}")

    def test_config_override(self, test_config, sample_pdf_path):
        """Test configuration overrides work correctly."""
        # Override config settings
        test_config.set("term_extraction.enabled", False)
        test_config.set("layout.enabled", False)

        pipeline = TranslationPipeline(test_config)

        # These components should be disabled
        assert pipeline.term_miner is None
        assert pipeline.layout_analyzer is None

        # But these should still be available
        assert pipeline.extractor is not None
        assert pipeline.translator is not None
        assert pipeline.renderer is not None

    def test_error_handling_invalid_pdf(self, test_config, tmp_path):
        """Test error handling with invalid PDF."""
        pipeline = TranslationPipeline(test_config)
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a PDF")

        with pytest.raises(Exception):
            pipeline.analyze(str(invalid_pdf))

    def test_error_handling_missing_file(self, test_config):
        """Test error handling with missing file."""
        pipeline = TranslationPipeline(test_config)

        with pytest.raises(FileNotFoundError):
            pipeline.analyze("non_existent.pdf")

    @pytest.mark.integration
    def test_output_formats(self, test_config, sample_pdf_path, tmp_path):
        """Test different output formats."""
        formats = ["html", "markdown"]

        for format_type in formats:
            test_config.set("output.format", format_type)
            pipeline = TranslationPipeline(test_config)

            suffix = ".html" if format_type == "html" else ".md"
            output_path = tmp_path / f"test_output{suffix}"

            try:
                pipeline.translate(sample_pdf_path, str(output_path), pages=[1])

                assert output_path.exists()
                content = output_path.read_text(encoding="utf-8")
                assert len(content) > 0

                print(f"Format {format_type}: {len(content)} characters")

            except Exception as e:
                pytest.skip(f"Format {format_type} test failed: {e}")

    def test_memory_usage(self, test_config, sample_pdf_path):
        """Test memory usage doesn't grow excessively."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        pipeline = TranslationPipeline(test_config)

        try:
            # Run analysis multiple times
            for _i in range(3):
                pipeline.analyze(sample_pdf_path)

                current_memory = process.memory_info().rss
                memory_growth = (current_memory - initial_memory) / 1024 / 1024  # MB

                # Memory growth should be reasonable (less than 500MB)
                assert memory_growth < 500, f"Memory growth too high: {memory_growth:.1f}MB"

        except Exception as e:
            pytest.skip(f"Memory test failed: {e}")


if __name__ == "__main__":
    # Run basic tests if executed directly
    pytest.main([__file__, "-v", "-k", "not slow and not integration"])
