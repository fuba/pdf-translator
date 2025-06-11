# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF自動翻訳ソフトウェア - A PDF translation system that preserves layout while translating documents up to 50 pages using local LLMs (Gemma 3 via Ollama) or OpenAI API.

## Key Architecture Components

### Module Structure
- **extractor**: PDF text extraction & OCR (PyMuPDF, PaddleOCR)
- **layout_analyzer**: Layout detection for columns, tables, figures (LayoutLM, DiT)
- **term_miner**: Technical term extraction & translation lookup (spaCy, Wikipedia API)
- **translator**: LLM integration for translation (Ollama/OpenAI)
- **post_processor**: Source term annotation & spacing adjustment
- **renderer**: HTML/Markdown output generation (Jinja2, Markdown-it-py)

### Translation Flow
1. Extract text with coordinates from PDF
2. Analyze layout structure
3. Extract technical terms and find translations
4. Translate page-by-page via LLM
5. Post-process to add source terms and adjust spacing
6. Render to HTML/Markdown preserving layout

## Development Commands

```bash
# Install dependencies
make install          # Production dependencies only
make dev-install      # All dependencies including dev tools

# Run Ollama for local LLM
make run-ollama       # Start server and ensure gemma3:12b is available
# Or manually:
ollama serve
ollama pull gemma3:12b

# Run tests
make test             # or: uv run pytest tests/

# Code quality
make lint             # Run linting with ruff
make format           # Format code with ruff
make type-check       # Type checking with mypy
make check            # Run all checks (lint, type-check, test)

# Clean up
make clean            # Remove cache and temporary files

# Quick test
make test-translate   # Test translation with sample PDF
```

## Configuration

The system uses `config.yml` for settings:
- Translation engine: ollama (default) or openai
- Model selection for each engine
- Language settings (source: auto, target: ja)
- Layout preservation options
- Output format (markdown/html)

## Important Constraints

- Maximum 50 pages per PDF
- Figures and tables are not translated (preserved as-is)
- Technical terms show as "訳語（原語）" on first occurrence
- Page breaks must be preserved (no text crossing pages)
- All tools should be free/open-source where possible

## LLM Integration

- Primary: Gemma 3 via Ollama (OpenAI API compatible)
- Fallback: OpenAI GPT-3.5/4
- System prompt emphasizes layout preservation and term annotation

## Environment Setup Knowledge

### UV Package Manager Issues
- UV command may not be in PATH after installation
- Use `./run-uv.sh` wrapper script to handle path resolution
- Script checks common installation paths and sources shell configs
- All Makefile commands use UV wrapper for consistency

### Dependencies and Models
- Total of 120+ packages including ML/AI libraries
- PaddleOCR requires large downloads (~35MB for opencv)
- PyTorch/transformers require ~65MB+ downloads
- spaCy Japanese model: `ja_core_news_sm` (12MB + 72MB sudachi dict)
- Ollama models should be verified with direct API calls, not Python client

### Development Environment
- Use `test_setup.py` to verify all components work correctly
- Key directories: logs/, output/, cache/, tests/fixtures/
- Configuration via config/config.yml and .env files
- PaddleOCR shows ccache warning (can be ignored)

### Common Commands
```bash
# Environment verification
./run-uv.sh run python test_setup.py

# Install/update dependencies  
make dev-install

# Quick checks
make check  # runs lint, type-check, test

# Ollama verification
curl -s http://localhost:11434/api/tags | jq .
```