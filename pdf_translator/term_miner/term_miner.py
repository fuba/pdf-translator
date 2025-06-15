"""Term mining and translation lookup module."""
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
from pdf_translator.config.manager import ConfigManager

# spaCy import with error handling
try:
    import spacy
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False

logger = logging.getLogger(__name__)


@dataclass
class TermMinerConfig:
    """Configuration for term mining."""

    enabled: bool = True
    min_frequency: int = 2  # Minimum frequency for term extraction
    max_terms: int = 100  # Maximum terms to extract per document
    wikipedia_lookup: bool = True  # Look up terms in Wikipedia
    languages: List[str] = field(default_factory=lambda: ["en", "ja"])
    spacy_models: Dict[str, str] = field(default_factory=lambda: {
        "en": "en_core_web_sm",
        "ja": "ja_core_news_sm"
    })
    cache_dir: Optional[str] = None  # Cache directory for translations

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TermMinerConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})


@dataclass
class Term:
    """Represents an extracted term with metadata."""

    text: str
    frequency: int
    context: str = ""  # Context where the term appears
    translations: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0  # Confidence score for term extraction
    category: str = "general"  # Term category (technical, medical, etc.)

    def __post_init__(self):
        """Normalize term text."""
        self.text = self.text.strip()


@dataclass
class TermExtractionResult:
    """Result of term extraction operation."""

    terms: List[Term]
    success: bool = True
    error: Optional[str] = None
    total_terms_found: int = 0
    filtered_terms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_translations_dict(self, target_lang: str = "ja") -> Dict[str, str]:
        """Get translations as a simple dictionary."""
        return {
            term.text: term.translations.get(target_lang, term.text)
            for term in self.terms
            if target_lang in term.translations
        }


class WikipediaLookup:
    """Wikipedia API lookup for term translations."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
        self.search_url = "https://{lang}.wikipedia.org/w/api.php"

    def lookup_term(self, term: str, source_lang: str = "en",
                   target_lang: str = "ja") -> Optional[Dict[str, Any]]:
        """Look up term translation and definition in Wikipedia."""
        try:
            # First, search for the term
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": term,
                "srlimit": 1,
                "srprop": "snippet"
            }

            search_url = f"https://{source_lang}.wikipedia.org/w/api.php"
            search_response = requests.get(
                search_url,
                params=search_params,
                timeout=self.timeout
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            if not search_data.get("query", {}).get("search"):
                return None

            # Get the page title
            page_title = search_data["query"]["search"][0]["title"]

            # Get page info with langlinks
            page_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|langlinks",
                "titles": page_title,
                "exintro": True,
                "explaintext": True,
                "exsentences": 2,
                "llprop": "langname",
                "lllang": target_lang
            }

            page_response = requests.get(
                search_url,
                params=page_params,
                timeout=self.timeout
            )
            page_response.raise_for_status()
            page_data = page_response.json()

            pages = page_data.get("query", {}).get("pages", {})
            if not pages:
                return None

            page_info = next(iter(pages.values()))

            # Extract translation from langlinks
            translation = None
            langlinks = page_info.get("langlinks", [])
            for link in langlinks:
                if link.get("lang") == target_lang:
                    translation = link.get("title")
                    break

            if not translation:
                return None

            return {
                "translation": translation,
                "extract": page_info.get("extract", ""),
                "source_title": page_title,
                "confidence": 0.8  # Wikipedia translations are generally reliable
            }

        except Exception as e:
            logger.warning(f"Wikipedia lookup failed for '{term}': {str(e)}")
            return None


class TermMiner:
    """Extract and manage technical terms from text."""

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.miner_config = TermMinerConfig()
        self.nlp_models = {}
        self.wikipedia = WikipediaLookup() if self.miner_config.wikipedia_lookup else None

        if not HAS_SPACY:
            logger.warning("spaCy not available. Term extraction will be limited.")

    def _load_spacy_model(self, language: str) -> Optional[Any]:
        """Load spaCy model for given language."""
        if not HAS_SPACY:
            return None

        if language in self.nlp_models:
            return self.nlp_models[language]

        model_name = self.miner_config.spacy_models.get(language)
        if not model_name:
            logger.warning(f"No spaCy model configured for language: {language}")
            return None

        try:
            nlp = spacy.load(model_name)
            self.nlp_models[language] = nlp
            return nlp
        except Exception as e:
            logger.error(f"Failed to load spaCy model '{model_name}': {str(e)}")
            return None

    def extract_terms(self, text: str, source_lang: str = "en") -> TermExtractionResult:
        """Extract terms from text."""
        if not self.miner_config.enabled:
            return TermExtractionResult(terms=[], success=True)

        try:
            # Load spaCy model
            nlp = self._load_spacy_model(source_lang)

            if nlp is None:
                # Fallback to simple pattern-based extraction
                return self._extract_terms_fallback(text)

            # Process text with spaCy
            doc = nlp(text)

            # Extract terms using multiple methods
            terms = []

            # 1. Named entities
            entity_terms = self._extract_named_entities(doc, text)
            terms.extend(entity_terms)

            # 2. Noun phrases (technical terms often appear as noun phrases)
            noun_phrase_terms = self._extract_noun_phrases(doc, text)
            terms.extend(noun_phrase_terms)

            # 3. Capitalized words and acronyms
            acronym_terms = self._extract_acronyms(text)
            terms.extend(acronym_terms)

            # Count frequencies and merge similar terms
            terms = self._count_frequencies(terms)
            terms = self._merge_similar_terms(terms)

            # Filter by frequency
            original_count = len(terms)
            terms = self._filter_terms_by_frequency(terms, self.miner_config.min_frequency)
            filtered_count = len(terms)

            # Limit number of terms
            terms = self._limit_terms(terms, self.miner_config.max_terms)

            # Add translations if enabled
            if self.miner_config.wikipedia_lookup and self.wikipedia:
                terms = self._add_translations(terms, source_lang)

            return TermExtractionResult(
                terms=terms,
                success=True,
                total_terms_found=original_count,
                filtered_terms=filtered_count,
                metadata={"method": "spacy", "model": nlp.meta.get("name", "unknown")}
            )

        except Exception as e:
            logger.error(f"Term extraction failed: {str(e)}")
            return TermExtractionResult(
                terms=[],
                success=False,
                error=str(e)
            )

    def _extract_terms_fallback(self, text: str) -> TermExtractionResult:
        """Fallback term extraction without spaCy."""
        try:
            terms = []

            # Extract capitalized words and acronyms
            acronym_terms = self._extract_acronyms(text)
            terms.extend(acronym_terms)

            # Extract common technical patterns
            pattern_terms = self._extract_technical_patterns(text)
            terms.extend(pattern_terms)

            # Count frequencies
            terms = self._count_frequencies(terms)
            terms = self._filter_terms_by_frequency(terms, self.miner_config.min_frequency)
            terms = self._limit_terms(terms, self.miner_config.max_terms)

            return TermExtractionResult(
                terms=terms,
                success=True,
                metadata={"method": "fallback"}
            )

        except Exception as e:
            return TermExtractionResult(
                terms=[],
                success=False,
                error=str(e)
            )

    def _extract_named_entities(self, doc: Any, text: str) -> List[Term]:
        """Extract named entities as terms."""
        terms = []

        for ent in doc.ents:
            # Focus on technical/scientific entities
            if ent.label_ in ["ORG", "PRODUCT", "TECHNOLOGY", "WORK_OF_ART", "EVENT"]:
                context = self._extract_context(text, ent.text, ent.start_char)
                term = Term(
                    text=ent.text,
                    frequency=1,
                    context=context,
                    category="entity",
                    confidence=0.9
                )
                terms.append(term)

        return terms

    def _extract_noun_phrases(self, doc: Any, text: str) -> List[Term]:
        """Extract noun phrases that might be technical terms."""
        terms = []

        for chunk in doc.noun_chunks:
            # Filter noun phrases by length and pattern
            if (2 <= len(chunk.text.split()) <= 4 and
                not chunk.text.lower().startswith(('the ', 'a ', 'an ')) and
                any(token.pos_ in ["NOUN", "PROPN"] for token in chunk)):

                context = self._extract_context(text, chunk.text, chunk.start_char)
                term = Term(
                    text=chunk.text,
                    frequency=1,
                    context=context,
                    category="noun_phrase",
                    confidence=0.7
                )
                terms.append(term)

        return terms

    def _extract_acronyms(self, text: str) -> List[Term]:
        """Extract acronyms and capitalized terms."""
        terms = []

        # Pattern for acronyms (2-6 uppercase letters)
        acronym_pattern = r'\b[A-Z]{2,6}\b'
        acronyms = re.findall(acronym_pattern, text)

        for acronym in acronyms:
            # Skip common words that are all caps
            if acronym.lower() not in ['and', 'or', 'the', 'for', 'with', 'pdf', 'url']:
                context = self._extract_context(text, acronym, text.find(acronym))
                term = Term(
                    text=acronym,
                    frequency=1,
                    context=context,
                    category="acronym",
                    confidence=0.8
                )
                terms.append(term)

        return terms

    def _extract_technical_patterns(self, text: str) -> List[Term]:
        """Extract technical terms using patterns."""
        terms = []

        # Common technical term patterns
        patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Title Case terms like "Machine Learning"
            # Terms with acronyms like "Application Programming Interface (API)"
            r'\b\w+\s*\([A-Z]+\)\b',
            r'\b\w+-\w+\b',  # Hyphenated terms
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match.split()) <= 3:  # Limit to reasonable length
                    context = self._extract_context(text, match, text.find(match))
                    term = Term(
                        text=match,
                        frequency=1,
                        context=context,
                        category="pattern",
                        confidence=0.6
                    )
                    terms.append(term)

        return terms

    def _extract_context(self, text: str, term: str, position: int,
                        window: int = 50) -> str:
        """Extract context around a term."""
        start = max(0, position - window)
        end = min(len(text), position + len(term) + window)
        return text[start:end].strip()

    def _count_frequencies(self, terms: List[Term]) -> List[Term]:
        """Count term frequencies and merge duplicates."""
        term_counts = Counter()
        term_objects = {}

        for term in terms:
            normalized = term.text.lower().strip()
            term_counts[normalized] += 1

            # Keep the term object with highest confidence
            if (normalized not in term_objects or
                term.confidence > term_objects[normalized].confidence):
                term_objects[normalized] = term

        # Update frequencies
        result_terms = []
        for normalized, count in term_counts.items():
            term = term_objects[normalized]
            term.frequency = count
            result_terms.append(term)

        return result_terms

    def _merge_similar_terms(self, terms: List[Term]) -> List[Term]:
        """Merge similar terms (case variations, etc.)."""
        merged = {}

        for term in terms:
            key = term.text.lower().strip()

            if key in merged:
                # Merge frequencies
                merged[key].frequency += term.frequency
                # Keep better context if available
                if len(term.context) > len(merged[key].context):
                    merged[key].context = term.context
            else:
                merged[key] = term

        return list(merged.values())

    def _filter_terms_by_frequency(self, terms: List[Term],
                                  min_frequency: int) -> List[Term]:
        """Filter terms by minimum frequency."""
        return [term for term in terms if term.frequency >= min_frequency]

    def _limit_terms(self, terms: List[Term], max_terms: int) -> List[Term]:
        """Limit number of terms, keeping highest frequency ones."""
        # Sort by frequency (descending) and confidence
        sorted_terms = sorted(
            terms,
            key=lambda t: (t.frequency, t.confidence),
            reverse=True
        )
        return sorted_terms[:max_terms]

    def _add_translations(self, terms: List[Term], source_lang: str) -> List[Term]:
        """Add translations to terms using Wikipedia lookup."""
        if not self.wikipedia:
            return terms

        target_lang = "ja"  # Default target language

        for term in terms:
            if len(term.translations) == 0:  # Only lookup if no translation exists
                translation_data = self.wikipedia.lookup_term(
                    term.text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )

                if translation_data:
                    term.translations[target_lang] = translation_data["translation"]
                    term.confidence = min(term.confidence, translation_data.get("confidence", 0.8))

        return terms
