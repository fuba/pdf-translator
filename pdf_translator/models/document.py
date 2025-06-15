"""Document model for PDF translator."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from .page import Page


@dataclass
class Document:
    """Represents a complete PDF document."""
    
    pages: List[Page]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        return len(self.pages)
    
    @property
    def has_text(self) -> bool:
        """Check if document contains any text."""
        return any(page.has_text for page in self.pages)
    
    @property
    def has_images(self) -> bool:
        """Check if document contains any images."""
        return any(page.has_images for page in self.pages)
    
    def get_page(self, page_number: int) -> Optional[Page]:
        """Get page by number (1-indexed)."""
        if 1 <= page_number <= len(self.pages):
            return self.pages[page_number - 1]
        return None
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Document(pages={self.page_count}, has_text={self.has_text})"