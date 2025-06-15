#!/usr/bin/env python3
"""
PDF Translation System - Main CLI Application

A complete PDF translation system that preserves layout while translating documents.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from pdf_translator.config.manager import ConfigManager
from pdf_translator.core.pipeline import TranslationPipeline
from pdf_translator.utils.logging import setup_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PDF Translation System - Translate PDFs while preserving layout",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate a PDF using default settings (Ollama/Gemma3)
  %(prog)s input.pdf

  # Translate to specific output file
  %(prog)s input.pdf -o translated.html

  # Use OpenAI instead of Ollama
  %(prog)s input.pdf --engine openai

  # Specify output format
  %(prog)s input.pdf --format markdown

  # Enable verbose logging
  %(prog)s input.pdf -v

  # Process specific pages only
  %(prog)s input.pdf --pages 1-10
        """
    )

    # Required arguments
    parser.add_argument(
        "input",
        type=str,
        help="Input PDF file path"
    )

    # Optional arguments
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: auto-generated based on input)"
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config/config.yml",
        help="Configuration file path (default: config/config.yml)"
    )

    parser.add_argument(
        "--engine",
        type=str,
        choices=["ollama", "openai"],
        default=None,
        help="Translation engine to use (default: from config)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name for translation (default: from config)"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["html", "markdown"],
        default=None,
        help="Output format (default: from config)"
    )

    parser.add_argument(
        "--source-lang",
        type=str,
        default=None,
        help="Source language code (default: auto-detect)"
    )

    parser.add_argument(
        "--target-lang",
        type=str,
        default=None,
        help="Target language code (default: ja)"
    )

    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Page range to process (e.g., '1-10', '1,3,5-7')"
    )

    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Force OCR processing even for text PDFs"
    )

    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR processing"
    )

    parser.add_argument(
        "--no-terms",
        action="store_true",
        help="Disable technical term extraction"
    )

    parser.add_argument(
        "--no-layout",
        action="store_true",
        help="Disable layout analysis (simple linear output)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all output except errors"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze PDF without translation (useful for testing)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    return parser.parse_args()


def validate_input(args: argparse.Namespace) -> None:
    """Validate input arguments."""
    # Check input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")
    
    if not input_path.suffix.lower() == ".pdf":
        raise ValueError(f"Input file must be a PDF: {args.input}")
    
    # Check config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {args.config}")
    
    # Validate page range if specified
    if args.pages:
        try:
            parse_page_range(args.pages)
        except ValueError as e:
            raise ValueError(f"Invalid page range: {e}")


def parse_page_range(page_range: str) -> list[int]:
    """Parse page range string into list of page numbers."""
    pages = []
    parts = page_range.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            start = int(start.strip())
            end = int(end.strip())
            if start > end:
                raise ValueError(f"Invalid range: {start}-{end}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    
    return sorted(set(pages))


def generate_output_path(input_path: Path, format: str) -> Path:
    """Generate output file path based on input and format."""
    suffix = ".html" if format == "html" else ".md"
    output_name = input_path.stem + "_translated" + suffix
    return input_path.parent / output_name


def main() -> int:
    """Main entry point."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Validate input
        validate_input(args)
        
        # Setup logging
        log_level = logging.WARNING if args.quiet else (
            logging.DEBUG if args.verbose else logging.INFO
        )
        setup_logging(level=log_level)
        logger = logging.getLogger(__name__)
        
        # Load configuration
        config = ConfigManager(args.config)
        
        # Override config with command line arguments
        if args.engine:
            config.set("translation.engine", args.engine)
        if args.model:
            config.set(f"translation.{args.engine or config.get('translation.engine')}.model", args.model)
        if args.format:
            config.set("output.format", args.format)
        if args.source_lang:
            config.set("translation.source_language", args.source_lang)
        if args.target_lang:
            config.set("translation.target_language", args.target_lang)
        
        # Set processing flags
        if args.ocr:
            config.set("extraction.force_ocr", True)
        if args.no_ocr:
            config.set("extraction.enable_ocr", False)
        if args.no_terms:
            config.set("term_extraction.enabled", False)
        if args.no_layout:
            config.set("layout.enabled", False)
        
        # Parse page range
        pages = parse_page_range(args.pages) if args.pages else None
        
        # Generate output path if not specified
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else generate_output_path(
            input_path, config.get("output.format", "html")
        )
        
        # Log configuration
        logger.info(f"Processing: {input_path}")
        logger.info(f"Output: {output_path}")
        logger.info(f"Engine: {config.get('translation.engine')}")
        logger.info(f"Format: {config.get('output.format')}")
        
        if not args.quiet:
            print(f"📄 Processing: {input_path}")
            print(f"🚀 Engine: {config.get('translation.engine')}")
            print(f"📝 Output: {output_path}")
        
        # Create and run pipeline
        pipeline = TranslationPipeline(config)
        
        if args.dry_run:
            # Dry run - only analyze
            if not args.quiet:
                print("\n🔍 Analyzing PDF (dry run)...")
            
            result = pipeline.analyze(str(input_path), pages=pages)
            
            print(f"\n📊 Analysis Results:")
            print(f"  Pages: {result['total_pages']}")
            print(f"  Text pages: {result['text_pages']}")
            print(f"  Image pages: {result['image_pages']}")
            print(f"  Total characters: {result['total_chars']}")
            
            if result.get('terms'):
                print(f"  Technical terms found: {len(result['terms'])}")
                print("  Sample terms:")
                for term in result['terms'][:5]:
                    print(f"    - {term}")
        else:
            # Full translation
            if not args.quiet:
                print("\n🔄 Starting translation...")
            
            result = pipeline.translate(
                str(input_path),
                str(output_path),
                pages=pages
            )
            
            if not args.quiet:
                print(f"\n✅ Translation completed!")
                print(f"📄 Output saved to: {output_path}")
                print(f"⏱️  Time: {result['processing_time']:.1f}s")
                print(f"📊 Pages processed: {result['pages_processed']}")
                
                if result.get('terms_extracted'):
                    print(f"🔤 Terms extracted: {result['terms_extracted']}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Translation cancelled by user")
        return 130
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())