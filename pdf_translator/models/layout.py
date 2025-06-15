"""Layout models for PDF translator."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class RegionType(Enum):
    """Types of layout regions."""

    TITLE = "title"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    HEADER = "header"
    FOOTER = "footer"
    UNKNOWN = "unknown"


@dataclass
class Region:
    """Represents a layout region on a page."""

    type: RegionType
    x: float
    y: float
    width: float
    height: float
    confidence: float = 1.0
    text: Optional[str] = None

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box as (x0, y0, x1, y1)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of region."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        """Get area of region."""
        return self.width * self.height

    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is within region."""
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def overlaps(self, other: "Region") -> bool:
        """Check if this region overlaps with another."""
        x1_min, y1_min, x1_max, y1_max = self.bounds
        x2_min, y2_min, x2_max, y2_max = other.bounds

        return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Region(type={self.type.value}, "
            f"bounds=({self.x:.1f}, {self.y:.1f}, "
            f"{self.x + self.width:.1f}, {self.y + self.height:.1f}))"
        )
