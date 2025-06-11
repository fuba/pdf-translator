#!/usr/bin/env python3
"""Create persistent sample PDF files for testing"""

from pathlib import Path

import fitz  # PyMuPDF


def create_sample_pdf(output_path: Path) -> None:
    """Create a comprehensive sample PDF for testing"""
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
    page2.insert_text((70, 270), "• layout_analyzer: レイアウト解析", fontsize=12)
    page2.insert_text((70, 290), "• term_miner: 専門用語抽出", fontsize=12)
    page2.insert_text((70, 310), "• translator: LLM による翻訳", fontsize=12)
    page2.insert_text((70, 330), "• post_processor: 後処理", fontsize=12)
    page2.insert_text((70, 350), "• renderer: HTML/Markdown 出力", fontsize=12)

    # Page 3: Technical terms and algorithms
    page3 = doc.new_page()
    page3.insert_text((50, 100), "2. 技術用語・アルゴリズム", fontsize=16, fontname="Helvetica-Bold")
    page3.insert_text((50, 140), "以下の技術用語が文書に含まれています：", fontsize=12)
    page3.insert_text((70, 170), "• API (Application Programming Interface)", fontsize=12)
    page3.insert_text((70, 190), "• OCR (Optical Character Recognition)", fontsize=12)
    page3.insert_text((70, 210), "• LLM (Large Language Model)", fontsize=12)
    page3.insert_text((70, 230), "• Transformer アーキテクチャ", fontsize=12)
    page3.insert_text((70, 250), "• PyTorch および spaCy ライブラリ", fontsize=12)
    page3.insert_text((70, 270), "• BERT, GPT-4, Gemma などの言語モデル", fontsize=12)

    page3.insert_text((50, 320), "2.1 処理アルゴリズム", fontsize=14, fontname="Helvetica-Bold")
    page3.insert_text((50, 350), "1. PDFからテキスト抽出", fontsize=12)
    page3.insert_text((50, 370), "2. レイアウト構造解析", fontsize=12)
    page3.insert_text((50, 390), "3. 専門用語の抽出と辞書作成", fontsize=12)
    page3.insert_text((50, 410), "4. 文脈を考慮した機械翻訳", fontsize=12)
    page3.insert_text((50, 430), "5. 用語注釈の付与", fontsize=12)
    page3.insert_text((50, 450), "6. 最終レンダリング", fontsize=12)

    doc.save(output_path)
    doc.close()

    print(f"Sample PDF created: {output_path}")


def create_english_sample_pdf(output_path: Path) -> None:
    """Create an English sample PDF for testing translation"""
    doc = fitz.open()

    # Page 1: Title page
    page1 = doc.new_page()
    page1.insert_text((50, 100), "Machine Learning Research Paper", fontsize=20, fontname="Helvetica-Bold")
    page1.insert_text((50, 150), "Deep Learning Approaches for Natural Language Processing", fontsize=16)
    page1.insert_text((50, 200), "Abstract", fontsize=14, fontname="Helvetica-Bold")
    page1.insert_text((50, 230), "This paper presents a comprehensive study of deep learning", fontsize=12)
    page1.insert_text((50, 250), "techniques applied to natural language processing tasks.", fontsize=12)
    page1.insert_text((50, 270), "We evaluate various neural network architectures including", fontsize=12)
    page1.insert_text((50, 290), "transformers, LSTMs, and attention mechanisms.", fontsize=12)

    # Page 2: Introduction
    page2 = doc.new_page()
    page2.insert_text((50, 100), "1. Introduction", fontsize=16, fontname="Helvetica-Bold")
    page2.insert_text((50, 140), "Natural Language Processing (NLP) has seen remarkable progress", fontsize=12)
    page2.insert_text((50, 160), "with the advent of deep learning. Key technologies include:", fontsize=12)
    page2.insert_text((70, 200), "• Recurrent Neural Networks (RNNs)", fontsize=12)
    page2.insert_text((70, 220), "• Long Short-Term Memory (LSTM) networks", fontsize=12)
    page2.insert_text((70, 240), "• Transformer architecture", fontsize=12)
    page2.insert_text((70, 260), "• Attention mechanisms", fontsize=12)
    page2.insert_text((70, 280), "• Pre-trained language models (BERT, GPT)", fontsize=12)

    page2.insert_text((50, 320), "1.1 Research Objectives", fontsize=14, fontname="Helvetica-Bold")
    page2.insert_text((50, 350), "Our primary research objectives are:", fontsize=12)
    page2.insert_text((50, 370), "1. Evaluate state-of-the-art NLP models", fontsize=12)
    page2.insert_text((50, 390), "2. Compare performance across different tasks", fontsize=12)
    page2.insert_text((50, 410), "3. Analyze computational efficiency", fontsize=12)

    doc.save(output_path)
    doc.close()

    print(f"English sample PDF created: {output_path}")


def main():
    """Create sample PDF files"""
    # Create output directory
    samples_dir = Path("tests/fixtures")
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Create Japanese sample PDF
    japanese_pdf = samples_dir / "sample_japanese.pdf"
    create_sample_pdf(japanese_pdf)

    # Create English sample PDF
    english_pdf = samples_dir / "sample_english.pdf"
    create_english_sample_pdf(english_pdf)

    print(f"\nSample files created in: {samples_dir}")
    print(f"Files: {list(samples_dir.glob('*.pdf'))}")


if __name__ == "__main__":
    main()
