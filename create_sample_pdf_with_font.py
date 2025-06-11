#!/usr/bin/env python3
"""Create sample PDF files with proper Japanese font support"""

from pathlib import Path

import fitz  # PyMuPDF


def check_system_fonts():
    """Check available Japanese fonts on the system"""
    print("Checking available Japanese fonts...")

    # Common Japanese font paths on macOS
    font_paths = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]

    available_fonts = []
    for font_path in font_paths:
        if Path(font_path).exists():
            available_fonts.append(font_path)
            print(f"  ✓ Found: {font_path}")

    return available_fonts


def create_text_only_japanese_pdf(output_path: Path) -> None:
    """Create a simple text-only Japanese PDF without embedded fonts"""
    doc = fitz.open()

    # Page 1: Title page
    page1 = doc.new_page()

    # Add text content that will be extracted (font rendering is handled by PDF viewer)
    text_content = """PDF自動翻訳システム
Automatic PDF Translation System

技術仕様書

このドキュメントはPDF翻訳システムのテスト用サンプルです。
様々なフォントサイズとレイアウトを含んでいます。

主な特徴：
• 最大50ページまでのPDF処理
• レイアウト保持機能
• 専門用語の自動抽出
• 日英・英日翻訳対応"""

    # Insert as text block
    page1.insert_textbox(
        fitz.Rect(50, 50, 500, 700),
        text_content,
        fontsize=12,
        align=0
    )

    # Page 2: Technical content
    page2 = doc.new_page()

    text_content2 = """1. システム概要

本システムはPyMuPDF、PaddleOCR、Ollamaを使用してPDFファイルの
自動翻訳を行います。レイアウト保持機能により、元の文書構造を
維持したまま翻訳が可能です。

1.1 主要コンポーネント
• extractor: PDF テキスト抽出
• layout_analyzer: レイアウト解析
• term_miner: 専門用語抽出
• translator: LLM による翻訳
• post_processor: 後処理
• renderer: HTML/Markdown 出力

1.2 処理フロー
1. PDFファイルの読み込み
2. テキストとレイアウト情報の抽出
3. 専門用語の識別と辞書作成
4. ページ単位での翻訳処理
5. 用語注釈の付与
6. 最終出力の生成"""

    page2.insert_textbox(
        fitz.Rect(50, 50, 500, 700),
        text_content2,
        fontsize=11,
        align=0
    )

    # Page 3: Technical terms
    page3 = doc.new_page()

    text_content3 = """2. 技術用語・アルゴリズム

以下の技術用語が文書に含まれています：
• API (Application Programming Interface)
• OCR (Optical Character Recognition) 
• LLM (Large Language Model)
• Transformer アーキテクチャ
• PyTorch および spaCy ライブラリ
• BERT, GPT-4, Gemma などの言語モデル

2.1 処理アルゴリズム
1. PDFからテキスト抽出
   - PyMuPDFを使用した高速処理
   - 文字位置情報の保持
   
2. レイアウト構造解析
   - LayoutLMによる文書構造認識
   - 段組み・表・図の識別
   
3. 専門用語の抽出と辞書作成
   - spaCyによる形態素解析
   - Wikipedia APIでの用語検索
   
4. 文脈を考慮した機械翻訳
   - Ollama/OpenAI APIの利用
   - プロンプトエンジニアリング
   
5. 用語注釈の付与
   - 初出時に「訳語（原語）」形式
   
6. 最終レンダリング
   - HTML/Markdown形式での出力"""

    page3.insert_textbox(
        fitz.Rect(50, 50, 500, 700),
        text_content3,
        fontsize=11,
        align=0
    )

    doc.save(output_path)
    doc.close()

    print(f"Text-based Japanese PDF created: {output_path}")


def create_mixed_content_pdf(output_path: Path) -> None:
    """Create a PDF with mixed Japanese and English content"""
    doc = fitz.open()

    # Create pages with mixed content
    page1 = doc.new_page()

    # Title section
    page1.insert_text((50, 80), "PDF Translation System", fontsize=20)
    page1.insert_text((50, 110), "Technical Specification Document", fontsize=14)

    # Mixed content
    mixed_text = """[System Overview / システム概要]

This document describes the PDF translation system that preserves
layout while translating documents between Japanese and English.

本システムは、PDFドキュメントのレイアウトを保持しながら
日本語と英語間の翻訳を行うシステムです。

Key Features / 主な機能:
• Layout preservation / レイアウト保持
• Technical term extraction / 専門用語抽出  
• Context-aware translation / 文脈考慮型翻訳
• Multi-page support (max 50 pages) / 複数ページ対応（最大50ページ）

Supported Technologies / 使用技術:
- PyMuPDF: PDF processing / PDF処理
- PaddleOCR: Optical character recognition / 光学文字認識
- Ollama/OpenAI: Translation engine / 翻訳エンジン
- spaCy: NLP processing / 自然言語処理"""

    page1.insert_textbox(
        fitz.Rect(50, 140, 500, 700),
        mixed_text,
        fontsize=11,
        align=0
    )

    doc.save(output_path)
    doc.close()

    print(f"Mixed content PDF created: {output_path}")


def main():
    """Create various sample PDF files"""
    # Check system fonts
    available_fonts = check_system_fonts()

    if not available_fonts:
        print("\n⚠️  Warning: No Japanese fonts found in standard locations")
        print("The PDFs will be created with text content, but Japanese characters")
        print("may not display correctly depending on your PDF viewer.\n")

    # Create output directory
    samples_dir = Path("tests/fixtures")
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Create text-based Japanese PDF
    japanese_pdf = samples_dir / "sample_japanese_text.pdf"
    create_text_only_japanese_pdf(japanese_pdf)

    # Create mixed content PDF
    mixed_pdf = samples_dir / "sample_mixed_content.pdf"
    create_mixed_content_pdf(mixed_pdf)

    # Keep the English PDF creation
    from create_sample_pdf import create_english_sample_pdf
    english_pdf = samples_dir / "sample_english.pdf"
    create_english_sample_pdf(english_pdf)

    print(f"\nSample files created in: {samples_dir}")
    print("Files created:")
    for pdf_file in samples_dir.glob("*.pdf"):
        print(f"  - {pdf_file.name}")

    print("\nNote: Japanese text extraction will work correctly even if")
    print("the characters don't display properly in your PDF viewer.")


if __name__ == "__main__":
    main()
