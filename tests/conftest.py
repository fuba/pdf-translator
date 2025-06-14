"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import fitz  # PyMuPDF
import pytest


@pytest.fixture
def sample_pdf() -> Generator[Path, None, None]:
    """Create a simple test PDF file."""
    # Create a temporary PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    # Create a simple PDF with PyMuPDF
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 100), "Test Document", fontsize=18)
    page1.insert_text((50, 150), "This is the first page of a test document.", fontsize=12)
    page1.insert_text((50, 200), "It contains multiple paragraphs for testing.", fontsize=12)

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 100), "Chapter 1", fontsize=16)
    page2.insert_text((50, 150), "This is the second page with different content.", fontsize=12)
    page2.insert_text((50, 200), "Here we have more text to analyze.", fontsize=12)
    page2.insert_text(
        (50, 250), "Technical terms like API and algorithm should be detected.", fontsize=12
    )

    doc.save(pdf_path)
    doc.close()

    yield pdf_path

    # Cleanup
    pdf_path.unlink()


@pytest.fixture
def empty_pdf() -> Generator[Path, None, None]:
    """Create an empty PDF file."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    doc = fitz.open()
    doc.new_page()  # Empty page
    doc.save(pdf_path)
    doc.close()

    yield pdf_path

    # Cleanup
    pdf_path.unlink()


@pytest.fixture
def large_pdf() -> Generator[Path, None, None]:
    """Create a PDF with many pages (for testing page limits)."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    doc = fitz.open()

    # Create 55 pages (exceeds the 50 page limit)
    for i in range(55):
        page = doc.new_page()
        page.insert_text((50, 100), f"Page {i + 1}", fontsize=12)
        page.insert_text((50, 150), f"Content for page {i + 1}", fontsize=10)

    doc.save(pdf_path)
    doc.close()

    yield pdf_path

    # Cleanup
    pdf_path.unlink()


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"
