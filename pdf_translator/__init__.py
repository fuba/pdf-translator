"""PDF Translation System - A tool for translating PDF documents while preserving layout."""

__version__ = "0.1.0"

# Import main components
from .config import ConfigManager
# from .core import TranslationPipeline  # TODO: Fix remaining issues
from .extractor import PDFExtractor, OCRExtractor, PageInfo, TextBlock
from .layout_analyzer import LayoutAnalyzer, LayoutRegion, RegionType
from .term_miner import TermMiner, Term, TermExtractionResult
from .translator import OllamaTranslator, OpenAITranslator, TranslatorFactory
from .post_processor import PostProcessor, PostProcessingResult
from .renderer import DocumentRenderer, AnnotatedDocument

__all__ = [
    "ConfigManager",
    # "TranslationPipeline",
    "PDFExtractor",
    "OCRExtractor", 
    "PageInfo",
    "TextBlock",
    "LayoutAnalyzer",
    "LayoutRegion",
    "RegionType",
    "TermMiner",
    "Term",
    "TermExtractionResult",
    "OllamaTranslator",
    "OpenAITranslator",
    "TranslatorFactory",
    "PostProcessor",
    "PostProcessingResult",
    "DocumentRenderer",
    "AnnotatedDocument",
]