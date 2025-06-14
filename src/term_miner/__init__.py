"""Term mining module for extracting and translating technical terms."""
from .term_miner import Term, TermExtractionResult, TermMiner, TermMinerConfig, WikipediaLookup

__all__ = [
    "TermMinerConfig",
    "Term",
    "TermMiner",
    "WikipediaLookup",
    "TermExtractionResult"
]
