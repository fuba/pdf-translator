"""Post-processing module for translation refinement and term annotation."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pdf_translator.config.manager import ConfigManager
from pdf_translator.term_miner import Term

logger = logging.getLogger(__name__)


@dataclass
class PostProcessorConfig:
    """Configuration for post-processing."""

    add_source_terms: bool = True  # Add source terms in parentheses
    source_term_format: str = "{translation}（{original}）"  # Format for term annotation
    spacing_adjustment: bool = True  # Adjust spacing between Japanese and English
    preserve_line_breaks: bool = True  # Preserve original line breaks
    min_term_length: int = 2  # Minimum term length for annotation
    max_annotations_per_term: int = 1  # Maximum annotations per unique term
    case_sensitive: bool = False  # Case-sensitive term matching

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PostProcessorConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})


@dataclass
class TermAnnotation:
    """Represents a term annotation."""

    original_term: str
    translated_term: str
    position: int
    first_occurrence: bool = True

    def format_annotation(self, format_string: str) -> str:
        """Format the annotation using the given format string."""
        return format_string.format(translation=self.translated_term, original=self.original_term)


@dataclass
class PostProcessingResult:
    """Result of post-processing operation."""

    processed_text: str
    success: bool = True
    error: Optional[str] = None
    annotations_added: int = 0
    terms_processed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PostProcessor:
    """Post-process translated text with term annotations and formatting."""

    def __init__(self, config: Optional[Union[ConfigManager, PostProcessorConfig]] = None):
        if isinstance(config, PostProcessorConfig):
            self.processor_config = config
            self.config = None
        else:
            self.config = config or ConfigManager()
            self.processor_config = PostProcessorConfig()
        self._annotation_count: Dict[str, int] = {}

    def process(
        self, translated_text: str, term_translations: Dict[str, str]
    ) -> PostProcessingResult:
        """Process translated text with term annotations."""
        if translated_text is None:
            return PostProcessingResult(
                processed_text="", success=False, error="Translated text is None"
            )

        try:
            processed_text = translated_text
            annotations_added = 0
            terms_processed = len(term_translations)

            # Reset annotation count for this processing session
            self._annotation_count.clear()

            if self.processor_config.add_source_terms and term_translations:
                processed_text, annotations_added = self._add_source_term_annotations(
                    processed_text, term_translations
                )

            if self.processor_config.spacing_adjustment:
                processed_text = self._adjust_spacing(processed_text)

            if self.processor_config.preserve_line_breaks:
                processed_text = self._preserve_formatting(processed_text)

            return PostProcessingResult(
                processed_text=processed_text,
                success=True,
                annotations_added=annotations_added,
                terms_processed=terms_processed,
            )

        except Exception as e:
            logger.error(f"Post-processing failed: {str(e)}")
            return PostProcessingResult(
                processed_text=translated_text,  # Return original on error
                success=False,
                error=str(e),
            )

    def process_with_terms(self, translated_text: str, terms: List[Term]) -> PostProcessingResult:
        """Process translated text using Term objects."""
        # Convert Term objects to translation dictionary
        term_translations = {}
        for term in terms:
            if len(term.text) >= self.processor_config.min_term_length:
                # Get Japanese translation if available
                translation = term.translations.get("ja", term.text)
                term_translations[term.text] = translation

        return self.process(translated_text, term_translations)

    def _add_source_term_annotations(
        self, text: str, term_translations: Dict[str, str]
    ) -> Tuple[str, int]:
        """Add source term annotations to translated text."""
        annotations_added = 0
        processed_text = text

        # Sort terms by translation length (longest first) to handle overlapping terms
        sorted_terms = sorted(
            term_translations.items(),
            key=lambda x: len(x[1]),  # Sort by translation length
            reverse=True,
        )

        # Keep track of already annotated positions to avoid overlaps
        annotated_positions: Set[Tuple[int, int]] = set()

        for original_term, translated_term in sorted_terms:
            # Skip if term is too short
            if len(original_term) < self.processor_config.min_term_length:
                continue

            # Skip if we've already annotated this term enough times
            if (
                self._annotation_count.get(original_term, 0)
                >= self.processor_config.max_annotations_per_term
            ):
                continue

            # Find the translated term in the text, avoiding overlaps
            processed_text, added, positions = self._annotate_term_with_positions(
                processed_text, original_term, translated_term, annotated_positions
            )
            annotations_added += added
            annotated_positions.update(positions)

        return processed_text, annotations_added

    def _annotate_term_with_positions(
        self,
        text: str,
        original_term: str,
        translated_term: str,
        annotated_positions: Set[Tuple[int, int]],
    ) -> Tuple[str, int, Set[Tuple[int, int]]]:
        """Annotate a specific term in the text, avoiding overlaps."""
        if not translated_term or translated_term.strip() == "":
            return text, 0, set()

        # Create the annotation
        annotation = self.processor_config.source_term_format.format(
            translation=translated_term, original=original_term
        )

        # Find and replace first occurrence only
        pattern_flags = 0 if self.processor_config.case_sensitive else re.IGNORECASE
        search_pattern = re.escape(translated_term)

        # Find the first occurrence that doesn't overlap with existing annotations
        for match in re.finditer(search_pattern, text, pattern_flags):
            start, end = match.span()

            # Check if this position overlaps with existing annotations
            overlaps = any(
                not (end <= existing_start or start >= existing_end)
                for existing_start, existing_end in annotated_positions
            )

            if not overlaps and self._annotation_count.get(original_term, 0) == 0:
                # Replace this occurrence
                before = text[:start]
                after = text[end:]
                new_text = before + annotation + after

                # Update annotation count
                self._annotation_count[original_term] = (
                    self._annotation_count.get(original_term, 0) + 1
                )

                # Calculate new position after annotation
                new_positions = {(start, start + len(annotation))}

                return new_text, 1, new_positions

        return text, 0, set()

    def _annotate_term(
        self, text: str, original_term: str, translated_term: str
    ) -> Tuple[str, int]:
        """Annotate a specific term in the text."""
        if not translated_term or translated_term.strip() == "":
            return text, 0

        # Create the annotation
        annotation = self.processor_config.source_term_format.format(
            translation=translated_term, original=original_term
        )

        # Find and replace first occurrence only
        pattern_flags = 0 if self.processor_config.case_sensitive else re.IGNORECASE

        # Use word boundaries to avoid partial matches
        # But be careful with Japanese text which doesn't use spaces
        search_pattern = re.escape(translated_term)

        # Find the first occurrence
        match = re.search(search_pattern, text, pattern_flags)
        if match:
            # Check if we haven't annotated this term yet
            if self._annotation_count.get(original_term, 0) == 0:
                # Replace only the first occurrence
                before = text[: match.start()]
                after = text[match.end() :]
                new_text = before + annotation + after

                # Update annotation count
                self._annotation_count[original_term] = (
                    self._annotation_count.get(original_term, 0) + 1
                )

                return new_text, 1

        return text, 0

    def _adjust_spacing(self, text: str) -> str:
        """Adjust spacing between Japanese and English text."""
        # Add space between Japanese and English characters
        # This is a basic implementation

        # Pattern for Japanese characters (Hiragana, Katakana, Kanji)
        japanese_pattern = r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]"
        # Pattern for ASCII characters (English, numbers, symbols)
        ascii_pattern = r"[A-Za-z0-9]"

        # Add space between Japanese and ASCII
        text = re.sub(f"({japanese_pattern})({ascii_pattern})", r"\1 \2", text)
        text = re.sub(f"({ascii_pattern})({japanese_pattern})", r"\1 \2", text)

        # Clean up multiple spaces
        text = re.sub(r" +", " ", text)

        return text

    def _preserve_formatting(self, text: str) -> str:
        """Preserve original formatting like line breaks."""
        # This is mainly to ensure we don't accidentally remove formatting
        # Most formatting should already be preserved by the processing logic

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Preserve paragraph breaks (double newlines)
        text = re.sub(r"\n\s*\n", "\n\n", text)

        return text

    def get_annotation_stats(self) -> Dict[str, int]:
        """Get statistics about annotations made."""
        return dict(self._annotation_count)

    def reset_annotations(self):
        """Reset annotation counting for new processing session."""
        self._annotation_count.clear()


class BatchPostProcessor:
    """Process multiple texts in batch."""

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.processor = PostProcessor(config)

    def process_batch(
        self, texts_and_terms: List[Tuple[str, Dict[str, str]]]
    ) -> List[PostProcessingResult]:
        """Process multiple texts with their respective term dictionaries."""
        results = []

        for text, term_dict in texts_and_terms:
            # Reset for each text to ensure proper first-occurrence tracking
            self.processor.reset_annotations()
            result = self.processor.process(text, term_dict)
            results.append(result)

        return results

    def process_pages(
        self, pages: List[str], global_terms: Dict[str, str]
    ) -> List[PostProcessingResult]:
        """Process multiple pages with shared global terms."""
        results = []

        # Track global first occurrences across all pages
        global_processor = PostProcessor(self.config)

        for page_text in pages:
            result = global_processor.process(page_text, global_terms)
            results.append(result)

        return results
