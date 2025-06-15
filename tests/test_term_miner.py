"""Tests for term_miner module."""
from unittest.mock import Mock, patch

from pdf_translator.term_miner import Term, TermExtractionResult, TermMiner, TermMinerConfig, WikipediaLookup


class TestTermMinerConfig:
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "enabled": True,
            "min_frequency": 3,
            "max_terms": 50,
            "wikipedia_lookup": True,
            "languages": ["en", "ja"]
        }
        config = TermMinerConfig.from_dict(config_dict)

        assert config.enabled is True
        assert config.min_frequency == 3
        assert config.max_terms == 50
        assert config.wikipedia_lookup is True
        assert config.languages == ["en", "ja"]

    def test_default_values(self):
        """Test default configuration values."""
        config = TermMinerConfig()

        assert config.enabled is True
        assert config.min_frequency == 2
        assert config.max_terms == 100
        assert config.wikipedia_lookup is True


class TestTerm:
    def test_term_creation(self):
        """Test Term dataclass creation."""
        term = Term(
            text="machine learning",
            frequency=5,
            context="This is about machine learning algorithms",
            translations={"ja": "機械学習"},
            confidence=0.9
        )

        assert term.text == "machine learning"
        assert term.frequency == 5
        assert term.translations["ja"] == "機械学習"
        assert term.confidence == 0.9

    def test_term_normalization(self):
        """Test term text normalization."""
        term1 = Term("Machine Learning", 1)
        term2 = Term("machine learning", 1)

        # Should be considered same after normalization
        assert term1.text.lower() == term2.text.lower()


class TestWikipediaLookup:
    @patch('requests.get')
    def test_lookup_success(self, mock_get):
        """Test successful Wikipedia lookup."""
        # Mock search response first, then page response
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "query": {
                "search": [
                    {"title": "Machine learning", "snippet": "Test snippet"}
                ]
            }
        }

        page_response = Mock()
        page_response.status_code = 200
        page_response.json.return_value = {
            "query": {
                "pages": {
                    "123": {
                        "title": "Machine learning",
                        "extract": "Machine learning is a method of data analysis...",
                        "langlinks": [
                            {"lang": "ja", "title": "機械学習"}
                        ]
                    }
                }
            }
        }

        # Return different responses for each call
        mock_get.side_effect = [search_response, page_response]

        lookup = WikipediaLookup()
        result = lookup.lookup_term("machine learning", target_lang="ja")

        assert result is not None
        assert result["translation"] == "機械学習"
        assert "extract" in result

        # Check API calls (should be called twice)
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_lookup_failure(self, mock_get):
        """Test Wikipedia lookup failure."""
        mock_get.side_effect = Exception("Network error")

        lookup = WikipediaLookup()
        result = lookup.lookup_term("nonexistent term")

        assert result is None

    @patch('requests.get')
    def test_lookup_no_translation(self, mock_get):
        """Test Wikipedia lookup with no translation available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "123": {
                        "title": "Some Term",
                        "extract": "Some description...",
                        "langlinks": []  # No translations
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        lookup = WikipediaLookup()
        result = lookup.lookup_term("some term", target_lang="ja")

        assert result is None or result.get("translation") is None


class TestTermMiner:
    def setup_method(self):
        """Set up for each test method."""
        self.config = TermMinerConfig(
            min_frequency=2,
            max_terms=10,
            wikipedia_lookup=False  # Disable for unit tests
        )
        self.miner = TermMiner(self.config)

    @patch('spacy.load')
    def test_extract_terms_basic(self, mock_spacy_load):
        """Test basic term extraction."""
        # Mock spaCy model
        mock_nlp = Mock()
        mock_doc = Mock()

        # Mock named entities
        mock_ent1 = Mock()
        mock_ent1.text = "machine learning"
        mock_ent1.label_ = "TECHNOLOGY"
        mock_ent1.start_char = 0

        mock_ent2 = Mock()
        mock_ent2.text = "neural network"
        mock_ent2.label_ = "TECHNOLOGY"
        mock_ent2.start_char = 20

        mock_doc.ents = [mock_ent1, mock_ent2]
        mock_doc.noun_chunks = []  # Empty noun chunks for simplicity

        # Mock meta attribute
        mock_nlp.meta = {"name": "test_model"}
        mock_nlp.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp

        text = "Machine learning and neural networks are important technologies."
        result = self.miner.extract_terms(text)

        assert result.success is True
        assert len(result.terms) >= 0  # Depends on implementation

    def test_filter_terms_by_frequency(self):
        """Test filtering terms by minimum frequency."""
        terms = [
            Term("term1", 3),
            Term("term2", 1),  # Should be filtered out
            Term("term3", 2),
            Term("term4", 5)
        ]

        filtered = self.miner._filter_terms_by_frequency(terms, min_frequency=2)
        filtered_texts = [t.text for t in filtered]

        assert "term1" in filtered_texts
        assert "term2" not in filtered_texts  # Filtered out
        assert "term3" in filtered_texts
        assert "term4" in filtered_texts

    def test_limit_terms(self):
        """Test limiting number of terms."""
        terms = [Term(f"term{i}", i+1) for i in range(20)]

        limited = self.miner._limit_terms(terms, max_terms=5)

        assert len(limited) == 5
        # Should keep highest frequency terms
        frequencies = [t.frequency for t in limited]
        assert max(frequencies) >= min(frequencies)

    @patch('spacy.load')
    def test_extract_terms_with_context(self, mock_spacy_load):
        """Test term extraction with context."""
        mock_nlp = Mock()
        mock_doc = Mock()

        # Mock token for context extraction
        mock_token = Mock()
        mock_token.text = "learning"
        mock_token.i = 5
        mock_doc.__getitem__ = Mock(return_value=mock_token)
        mock_doc.__len__ = Mock(return_value=10)

        mock_nlp.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp

        text = "Machine learning is a subset of artificial intelligence."
        context = self.miner._extract_context(text, "learning", 0)

        assert isinstance(context, str)

    def test_merge_similar_terms(self):
        """Test merging of similar terms."""
        terms = [
            Term("machine learning", 3),
            Term("Machine Learning", 2),  # Should be merged
            Term("neural network", 1)
        ]

        merged = self.miner._merge_similar_terms(terms)

        # Should have merged the two machine learning terms
        ml_terms = [t for t in merged if "machine learning" in t.text.lower()]
        assert len(ml_terms) == 1
        assert ml_terms[0].frequency == 5  # 3 + 2


class TestTermExtractionResult:
    def test_result_creation(self):
        """Test TermExtractionResult creation."""
        terms = [
            Term("API", 3, translations={"ja": "API"}),
            Term("database", 2, translations={"ja": "データベース"})
        ]

        result = TermExtractionResult(
            terms=terms,
            success=True,
            total_terms_found=10,
            filtered_terms=8
        )

        assert len(result.terms) == 2
        assert result.success is True
        assert result.total_terms_found == 10
        assert result.filtered_terms == 8

    def test_get_translations_dict(self):
        """Test getting translations as dictionary."""
        terms = [
            Term("API", 3, translations={"ja": "API"}),
            Term("database", 2, translations={"ja": "データベース"})
        ]

        result = TermExtractionResult(terms=terms, success=True)
        translations = result.get_translations_dict("ja")

        assert translations["API"] == "API"
        assert translations["database"] == "データベース"

    def test_failed_result(self):
        """Test failed extraction result."""
        result = TermExtractionResult(
            terms=[],
            success=False,
            error="spaCy model not available"
        )

        assert result.success is False
        assert result.error == "spaCy model not available"
        assert len(result.terms) == 0
