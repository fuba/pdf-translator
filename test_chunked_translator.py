#!/usr/bin/env python3
"""Test script for chunked translator."""

import logging
from pdf_translator.config.manager import ConfigManager
from pdf_translator.translator.chunked_translator import ChunkedTranslator

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_chunked_translator():
    """Test the chunked translator with a simple text."""
    # Initialize translator
    config = ConfigManager()
    translator = ChunkedTranslator(config)
    
    # Test text
    test_text = """Large Language Models (LLMs) have recently evolved to include specialized variants explicitly designed for reasoning tasks. These models are new artifacts, characterized by their "thinking" mechanisms such as long Chain-of-Thought (CoT) with self-reflection.

Recent generations of frontier language models have introduced Large Reasoning Models (LRMs) that generate detailed thinking processes before providing answers. While these models demonstrate improved performance on reasoning benchmarks, their fundamental capabilities remain insufficiently understood."""
    
    print(f"Original text length: {len(test_text)}")
    
    # Test chunking
    chunks = translator.chunker.chunk_text(test_text)
    print(f"Number of chunks: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {len(chunk.text)} chars")
        print(f"Preview: {chunk.text[:100]}...")
        print()
    
    # Test translation
    print("Testing translation...")
    results = translator.translate_chunked(test_text, "auto", "ja")
    
    print(f"Translation results: {len(results)}")
    for i, result in enumerate(results):
        print(f"Result {i}: Success={result.success}")
        if result.success:
            print(f"Translated: {result.translated_text[:200]}...")
        else:
            print(f"Error: {result.error}")
        print()
    
    # Test merge
    merged = translator.merge_translation_results(results)
    print(f"Merged translation length: {len(merged)}")
    print(f"Merged preview: {merged[:300]}...")

if __name__ == "__main__":
    test_chunked_translator()