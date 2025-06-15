"""Page model for PDF translator."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .layout import Region


@dataclass
class TextBlock:
    """Represents a block of text with position."""

    text: str
    x: float
    y: float
    width: float
    height: float
    font_size: Optional[float] = None
    font_name: Optional[str] = None

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box as (x0, y0, x1, y1)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def copy(self) -> "TextBlock":
        """Create a copy of this text block."""
        return TextBlock(
            text=self.text,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
            font_name=self.font_name,
        )


@dataclass
class Image:
    """Represents an image with position."""

    x: float
    y: float
    width: float
    height: float
    data: bytes = field(repr=False)
    format: str = "png"

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box as (x0, y0, x1, y1)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class Page:
    """Represents a single page in a PDF."""

    number: int
    width: float
    height: float
    text_blocks: List[TextBlock] = field(default_factory=list)
    images: List[Image] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)

    @property
    def has_text(self) -> bool:
        """Check if page contains text."""
        return len(self.text_blocks) > 0

    @property
    def has_images(self) -> bool:
        """Check if page contains images."""
        return len(self.images) > 0

    @property
    def text_content(self) -> str:
        """Get all text content as a single string."""
        return "\n".join(block.text for block in self.text_blocks)

    def add_text_block(self, block: TextBlock) -> None:
        """Add a text block to the page."""
        self.text_blocks.append(block)

    def add_image(self, image: Image) -> None:
        """Add an image to the page."""
        self.images.append(image)

    def add_region(self, region: Region) -> None:
        """Add a layout region to the page."""
        self.regions.append(region)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Page(number={self.number}, "
            f"text_blocks={len(self.text_blocks)}, "
            f"images={len(self.images)})"
        )
