# PDF自動翻訳ソフトウェア 仕様書

## 概要

本ドキュメントは、最大 **50 ページ** の PDF 文書を対象に、ローカル実行の大規模言語モデル（LLM）を用いて **日本語に自動翻訳** するソフトウェアの仕様をまとめたものです。主な目的は、原文 PDF の **レイアウトを可能な限り保持** しつつ、高品質な翻訳を実現することです。

---

## 主要要件

| 項目            | 内容                                                      |
| ------------- | ------------------------------------------------------- |
| **入力**        | テキスト PDF または 画像 PDF（OCR 必要）                             |
| **出力**        | HTML または Markdown 形式。ページ区切り・段落構造を維持                     |
| **対象ページ数**    | 最大 50 ページ                                               |
| **翻訳先言語**     | デフォルト: 日本語（設定で変更可）                                      |
| **図表**        | 翻訳しない（原文を維持または画像貼付）                                     |
| **レイアウト**     | 改行・段組み・ページ区切りを保持。訳文が短い場合は余白で調整しページをまたがない                |
| **専門用語**      | 自動抽出。初出時に「訳語（原語）」形式で併記                                  |
| **翻訳エンジン**    | Gemma 3（Ollama 経由、OpenAI API 互換）。必要に応じて OpenAI GPT を選択可 |
| **テキスト抽出**    | PyMuPDF + PaddleOCR。レイアウト解析に LayoutLM/DiT 併用            |
| **ライセンス/コスト** | すべて無料ツールを優先使用。外部 API を使う場合は OpenAI を第一候補                |

---

## アーキテクチャ概要

```mermaid
flowchart LR
    PDF[入力PDF]
    A[テキスト抽出 & レイアウト解析]
    B[専門用語抽出 & 対訳検索]
    C[LLM翻訳 (Gemma3 via Ollama)]
    D[後処理: 原語併記・改行調整]
    E[レイアウト再構築 & 出力生成]
    PDF --> A --> B
    B --> C --> D --> E[翻訳結果(HTML/Markdown)]
    A --> C
    A --> E
```

---

## 処理フロー詳細

1. **PDF テキスト抽出**
   - PyMuPDF でテキストブロックと座標を取得。
   - 画像 PDF は PaddleOCR で文字認識。
   - LayoutLM/DiT で段組み・表・図領域を判定。
2. **専門用語抽出**
   - キーワード抽出（YAKE / spaCy など）で固有名詞・略語を抽出。
   - Wikipedia 等から対訳候補を検索し用語集を作成。
3. **翻訳（LLM）**
   - ページ単位で Gemma 3 にプロンプト送信。
   - システム指示例:
     > "文章の意味を保持しつつ日本語に翻訳し、レイアウトを変えないでください。専門用語は初出時に原語を括弧書きで併記してください。"
4. **後処理**
   - 専門用語が正しく併記されているか検証。
   - 訳文が短い場合は余白（全角スペース）を付与。
5. **レイアウト再構築 & 出力**
   - 段落・見出しを Markdown/HTML 記法にマッピング。
   - ページ区切りは `---` (Markdown) または `<hr>` (HTML) で表現。
   - 図表は画像タグまたは元の PDF から抜き出した画像を埋め込み。

---

## モジュール構成

| モジュール                | 役割                 | 主要ライブラリ                          |
| -------------------- | ------------------ | -------------------------------- |
| **extractor**        | PDF テキスト抽出・OCR     | PyMuPDF, PaddleOCR               |
| **layout\_analyzer** | 段組み・表・図領域検出        | LayoutLM, DiT                    |
| **term\_miner**      | 専門用語抽出・対訳検索        | spaCy, Wikipedia API             |
| **translator**       | LLM 連携・翻訳実行        | Ollama (Gemma 3), OpenAI API     |
| **post\_processor**  | 原語併記・改行/余白調整       | Python (regex, diff-match-patch) |
| **renderer**         | HTML / Markdown 生成 | Jinja2, Markdown-it-py           |

---

## 設定ファイル例 (`config.yml`)

```yaml
translator:
  engine: ollama              # ollama / openai
  model: gemma3:12b-it-q8_0   # Ollama モデル名
  openai_model: gpt-3.5-turbo # engine=openai 用

source_language: auto
target_language: ja
preserve_format: true
include_source_term: true

use_ocr: true
layout_analysis: true
skip_elements: ["table", "figure", "code"]
max_pages: 50

output_format: markdown   # markdown / html
page_separator: hr        # hr / section
```

---

## 技術選定理由

- **Gemma 3 + Ollama**: ローカル実行で高性能。OpenAI API 互換で実装負担が少ない。
- **PyMuPDF**: 軽量・高速でテキスト座標が取得可能。
- **PaddleOCR**: 日本語対応の高精度 OCR。GPU 対応で高速。
- **LayoutLM/DiT**: 文書構造を抽出し、レイアウト保持に活用。

---

## 今後の拡張案

- 対訳 PDF 生成（原文と訳文を並列で表示）。
- ユーザ定義の専門用語辞書 (CSV) 取り込み。
- Web GUI での一括処理 & 進捗表示。
- GPT-4 等を用いた訳質レビュー支援機能。

---

## 参考情報

- Ollama: [https://github.com/ollama/ollama](https://github.com/ollama/ollama)
- Gemma 3 Model Card: [https://ai.google.dev/gemma](https://ai.google.dev/gemma)
- PyMuPDF: [https://pymupdf.readthedocs.io/](https://pymupdf.readthedocs.io/)
- PaddleOCR: [https://github.com/PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- LayoutLM/DiT: [https://github.com/microsoft/unilm](https://github.com/microsoft/unilm)

