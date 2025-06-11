#!/usr/bin/env python3
"""Demo script to test PDF extractor with a sample document"""

import tempfile
import fitz  # PyMuPDF
from pathlib import Path
from src.extractor import PDFExtractor
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json


def create_sample_pdf() -> Path:
    """Create a more comprehensive sample PDF for testing"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    doc = fitz.open()

    # Page 1: Title page with multiple font sizes
    page1 = doc.new_page()
    page1.insert_text((50, 100), "PDF自動翻訳システム", fontsize=24, fontname="Helvetica-Bold")
    page1.insert_text(
        (50, 150), "Automatic PDF Translation System", fontsize=18, fontname="Helvetica"
    )
    page1.insert_text((50, 200), "技術仕様書", fontsize=16, fontname="Helvetica-Bold")
    page1.insert_text(
        (50, 250), "このドキュメントはPDF翻訳システムのテスト用サンプルです。", fontsize=12
    )
    page1.insert_text((50, 280), "様々なフォントサイズとレイアウトを含んでいます。", fontsize=12)

    # Page 2: Technical content
    page2 = doc.new_page()
    page2.insert_text((50, 100), "1. システム概要", fontsize=16, fontname="Helvetica-Bold")
    page2.insert_text(
        (50, 140), "本システムはPyMuPDF、PaddleOCR、Ollamaを使用してPDFファイルの", fontsize=12
    )
    page2.insert_text(
        (50, 160), "自動翻訳を行います。レイアウト保持機能により、元の文書構造を", fontsize=12
    )
    page2.insert_text((50, 180), "維持したまま翻訳が可能です。", fontsize=12)

    page2.insert_text((50, 220), "1.1 主要コンポーネント", fontsize=14, fontname="Helvetica-Bold")
    page2.insert_text((70, 250), "• extractor: PDF テキスト抽出", fontsize=12)
    page2.insert_text((70, 270), "• translator: LLM による翻訳", fontsize=12)
    page2.insert_text((70, 290), "• renderer: HTML/Markdown 出力", fontsize=12)

    # Page 3: Technical terms
    page3 = doc.new_page()
    page3.insert_text((50, 100), "2. 技術用語", fontsize=16, fontname="Helvetica-Bold")
    page3.insert_text((50, 140), "以下の技術用語が文書に含まれています：", fontsize=12)
    page3.insert_text((70, 170), "• API (Application Programming Interface)", fontsize=12)
    page3.insert_text((70, 190), "• OCR (Optical Character Recognition)", fontsize=12)
    page3.insert_text((70, 210), "• LLM (Large Language Model)", fontsize=12)
    page3.insert_text((70, 230), "• Transformer アーキテクチャ", fontsize=12)
    page3.insert_text((70, 250), "• PyTorch および spaCy ライブラリ", fontsize=12)

    doc.save(pdf_path)
    doc.close()

    return pdf_path


def main():
    """Main demo function"""
    console = Console()

    console.print(Panel.fit("PDF Extractor Demo", style="bold blue"))

    # Create sample PDF
    console.print("\n[bold green]Creating sample PDF...[/bold green]")
    pdf_path = create_sample_pdf()
    console.print(f"Sample PDF created: {pdf_path}")

    try:
        # Initialize extractor
        console.print("\n[bold green]Initializing PDFExtractor...[/bold green]")
        extractor = PDFExtractor(max_pages=50)

        # Extract PDF
        console.print("\n[bold green]Extracting PDF content...[/bold green]")
        pages = extractor.extract_pdf(pdf_path)
        console.print(f"Extracted {len(pages)} pages")

        # Display page information
        for i, page in enumerate(pages):
            console.print(f"\n[bold yellow]Page {i + 1}:[/bold yellow]")
            console.print(f"  Dimensions: {page.width:.1f} x {page.height:.1f}")
            console.print(f"  Text blocks: {len(page.text_blocks)}")
            console.print(f"  Has images: {page.has_images}")

            # Display text blocks
            if page.text_blocks:
                table = Table(title=f"Text Blocks - Page {i + 1}")
                table.add_column("Type", style="cyan")
                table.add_column("Font", style="magenta")
                table.add_column("Size", style="green")
                table.add_column("Text", style="white")

                for block in page.text_blocks[:5]:  # Show first 5 blocks
                    text_preview = block.text[:50] + "..." if len(block.text) > 50 else block.text
                    table.add_row(
                        block.block_type, block.font_name, f"{block.font_size:.1f}", text_preview
                    )

                console.print(table)

        # Display layout analysis
        console.print("\n[bold green]Analyzing layout structure...[/bold green]")
        analysis = extractor.analyze_layout_structure(pages)

        analysis_table = Table(title="Layout Analysis")
        analysis_table.add_column("Property", style="cyan")
        analysis_table.add_column("Value", style="yellow")

        analysis_table.add_row("Total pages", str(analysis["total_pages"]))
        analysis_table.add_row("Average width", f"{analysis['average_page_width']:.1f}")
        analysis_table.add_row("Average height", f"{analysis['average_page_height']:.1f}")
        analysis_table.add_row("Pages with images", str(analysis["pages_with_images"]))
        analysis_table.add_row("Total text blocks", str(analysis["total_text_blocks"]))
        analysis_table.add_row("Font sizes", ", ".join(map(str, analysis["font_sizes"])))
        analysis_table.add_row(
            "Block types", ", ".join(f"{k}:{v}" for k, v in analysis["block_types"].items())
        )

        console.print(analysis_table)

        # Test utility methods
        console.print("\n[bold green]Testing utility methods...[/bold green]")
        text_by_page = extractor.get_text_by_page(pages)
        blocks_by_page = extractor.get_text_blocks_by_page(pages)

        console.print(f"Text by page keys: {list(text_by_page.keys())}")
        console.print(f"Text blocks by page keys: {list(blocks_by_page.keys())}")

        # Display extracted text for first page
        console.print("\n[bold yellow]Sample extracted text (Page 1):[/bold yellow]")
        console.print(Panel(text_by_page[0][:200] + "...", title="Raw Text"))

        console.print("\n[bold green]✓ PDF Extractor Demo completed successfully![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        raise

    finally:
        # Cleanup
        pdf_path.unlink()
        console.print(f"\nCleaned up temporary file: {pdf_path}")


if __name__ == "__main__":
    main()
