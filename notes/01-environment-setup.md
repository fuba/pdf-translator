# 01. 開発環境構築 作業記録

**実施日**: 2025年1月13日  
**担当**: Claude Code  
**ステータス**: ✅ 完了

## 概要

PDF翻訳ソフトウェアの開発環境を構築しました。uvパッケージマネージャーを使用したPython環境の構築、必要な依存関係のインストール、設定ファイルの作成を実施しました。

## 実施内容

### 1. Python環境の初期化

```bash
# uvでプロジェクトを初期化
uv init --name pdf-translator --python 3.11
```

**課題**: uvコマンドがPATHに正しく設定されていない問題が発生  
**解決策**: `run-uv.sh`ラッパースクリプトを作成し、複数のパスを確認する仕組みを導入

### 2. プロジェクト構造の作成

```
src/
├── extractor/          # PDF text extraction & OCR
├── layout_analyzer/    # Layout detection
├── term_miner/        # Technical term extraction
├── translator/        # LLM integration
├── post_processor/    # Source term annotation
└── renderer/          # HTML/Markdown output
```

### 3. 依存関係の定義・インストール

- **総パッケージ数**: 120個
- **主要ライブラリ**:
  - PyMuPDF (21.4MB): PDF処理
  - PaddleOCR (2.3MB) + PaddlePaddle (92.4MB): OCR
  - PyTorch (65.5MB) + Transformers (10.0MB): レイアウト解析
  - spaCy (6.1MB): 自然言語処理
  - Ollama (0.5.1): LLM連携

### 4. モデル・データのダウンロード

- **spaCy日本語モデル**: ja_core_news_sm (12.1MB)
- **Sudachi辞書**: sudachidict_core (72.1MB)
- **Ollama確認**: gemma3:12b モデルが利用可能

### 5. 設定ファイルの作成

- `config/config.yml`: メイン設定ファイル
- `.env.example`: 環境変数テンプレート
- `.gitignore`: Git除外設定
- `Makefile`: 開発タスク定義

### 6. 開発ツールの整備

- **uvラッパー**: `run-uv.sh` - PATH問題を解決
- **環境テスト**: `test_setup.py` - 全コンポーネントの動作確認
- **Makefile**: 開発コマンドの統一

## 技術的課題と解決策

### 課題1: uvコマンドのPATH問題
**問題**: `zsh: command not found: uv`  
**原因**: uvインストール後にPATHが正しく設定されていない  
**解決**: 複数パスをチェックするラッパースクリプトを作成

```bash
# 確認した場所
- $HOME/.cargo/bin/uv
- $HOME/.local/bin/uv  
- /usr/local/bin/uv
- /opt/homebrew/bin/uv
```

### 課題2: Ollama Pythonクライアントの互換性
**問題**: `ollama.Client().list()`で正しくモデル一覧が取得できない  
**解決**: 直接REST APIを使用する方式に変更

```python
# 問題のあるコード
models = ollama.Client().list()

# 解決策
response = requests.get("http://localhost:11434/api/tags")
data = response.json()
```

### 課題3: PaddleOCRの警告
**現象**: ccacheが見つからない警告が表示  
**対応**: 動作に影響なし、警告として記録

## 動作確認結果

環境テスト `test_setup.py` で全4項目をクリア:

1. ✅ **ライブラリインポート**: 9個の主要ライブラリが正常にインポート可能
2. ✅ **Ollama接続**: サーバー接続とgemma3:12bモデルの存在確認
3. ✅ **spaCy日本語モデル**: トークン化処理が正常動作
4. ✅ **プロジェクト構造**: 全必要ディレクトリが存在

## インストール容量

- **仮想環境**: .venv/ (~500MB)
- **モデル・辞書**: ~84MB (spaCy + Sudachi)
- **Ollama模型**: gemma3:12b (8.1GB) - 既存

## 次のステップ

- [ ] PDF抽出モジュール (extractor) の実装開始
- [ ] テストフレームワークのセットアップ
- [ ] CI/CD環境の検討

## 参考コマンド

```bash
# 環境確認
./run-uv.sh run python test_setup.py

# 開発開始
make dev-install
make check

# Ollama確認  
curl -s http://localhost:11434/api/tags | jq .
```