"""PDF Translation System - A tool for translating PDF documents while preserving layout."""

__version__ = "0.1.0"

# Import main components
from .config import ConfigManager

# from .core import TranslationPipeline  # TODO: Fix remaining issues
from .extractor import OCRExtractor, PageInfo, PDFExtractor, TextBlock
from .layout_analyzer import LayoutAnalyzer, LayoutRegion, RegionType
from .post_processor import PostProcessingResult, PostProcessor
from .renderer import AnnotatedDocument, DocumentRenderer
from .term_miner import Term, TermExtractionResult, TermMiner
from .translator import OllamaTranslator, OpenAITranslator, TranslatorFactory

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
