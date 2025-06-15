"""Chunked translation with context preservation."""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

from pdf_translator.config.manager import ConfigManager
from pdf_translator.translator.translator import (
    BaseTranslator, 
    TranslationResult, 
    TranslatorConfig,
    TranslatorFactory
)

logger = logging.getLogger(__name__)


@dataclass
class ChunkInfo:
    """Information about a text chunk."""
    text: str
    start_pos: int
    end_pos: int
    chunk_id: int
    is_paragraph_boundary: bool = False
    context_summary: Optional[str] = None


@dataclass 
class TranslationContext:
    """Context information for maintaining translation consistency."""
    previous_chunks: List[str] = field(default_factory=list)
    terminology: Dict[str, str] = field(default_factory=dict)
    style_notes: str = ""
    document_type: str = "technical"
    
    def get_summary(self, max_length: int = 500) -> str:
        """Get a summary of previous translation context."""
        if not self.previous_chunks:
            return ""
        
        # Combine recent chunks (last 2-3)
        recent_text = " ".join(self.previous_chunks[-3:])
        
        # Truncate if too long
        if len(recent_text) > max_length:
            recent_text = recent_text[:max_length] + "..."
        
        summary = f"Previous translation context: {recent_text}"
        
        if self.terminology:
            terms = ", ".join([f"{k}→{v}" for k, v in list(self.terminology.items())[:5]])
            summary += f"\nKey terminology: {terms}"
        
        if self.style_notes:
            summary += f"\nStyle notes: {self.style_notes}"
            
        return summary


class TextChunker:
    """Handles intelligent text chunking for translation."""
    
    def __init__(self, max_chunk_size: int = 2000, overlap_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
    
    def chunk_text(self, text: str) -> List[ChunkInfo]:
        """Split text into overlapping chunks with sentence boundaries."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_text = ""
        current_pos = 0
        chunk_id = 0
        
        for para_idx, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If adding this paragraph would exceed chunk size, finalize current chunk
            if current_text and len(current_text) + len(paragraph) > self.max_chunk_size:
                chunks.append(ChunkInfo(
                    text=current_text.strip(),
                    start_pos=current_pos,
                    end_pos=current_pos + len(current_text),
                    chunk_id=chunk_id,
                    is_paragraph_boundary=True
                ))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_text)
                current_text = overlap_text + "\n\n" + paragraph
                current_pos += len(current_text) - len(overlap_text) - len(paragraph) - 2
                chunk_id += 1
            else:
                # Add paragraph to current chunk
                if current_text:
                    current_text += "\n\n" + paragraph
                else:
                    current_text = paragraph
        
        # Add final chunk
        if current_text.strip():
            chunks.append(ChunkInfo(
                text=current_text.strip(),
                start_pos=current_pos,
                end_pos=current_pos + len(current_text),
                chunk_id=chunk_id,
                is_paragraph_boundary=True
            ))
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of current chunk."""
        if len(text) <= self.overlap_size:
            return text
            
        # Try to find sentence boundary
        sentences = re.split(r'[.!?]\s+', text)
        if len(sentences) > 1:
            # Take last sentence(s) for overlap
            overlap = sentences[-1]
            if len(overlap) < self.overlap_size // 2 and len(sentences) > 1:
                overlap = sentences[-2] + ". " + overlap
            return overlap
        
        # Fallback to character-based overlap
        return text[-self.overlap_size:]


class ChunkedTranslator:
    """Translator that processes text in chunks with context preservation."""
    
    def __init__(self, config: Optional[Union[ConfigManager, TranslatorConfig]] = None):
        if isinstance(config, TranslatorConfig):
            self.translator_config = config
            self.base_translator = TranslatorFactory.create(config)
        else:
            config_manager = config or ConfigManager()
            self.translator_config = TranslatorConfig.from_config_manager(config_manager)
            self.base_translator = TranslatorFactory.create(self.translator_config)
        
        self.chunker = TextChunker(max_chunk_size=1500, overlap_size=150)
        self.context = TranslationContext()
    
    def get_enhanced_system_prompt(
        self, 
        source_lang: str, 
        target_lang: str, 
        context_summary: str = ""
    ) -> str:
        """Generate enhanced system prompt with context."""
        base_prompt = self.base_translator.get_system_prompt(source_lang, target_lang)
        
        if context_summary:
            enhanced_prompt = f"""{base_prompt}

IMPORTANT CONTEXT INFORMATION:
{context_summary}

Please maintain consistency with the previous translation context, especially:
- Use the same terminology for technical terms
- Maintain the same writing style and tone
- Ensure smooth continuation from previous content

"""
        else:
            enhanced_prompt = base_prompt
        
        return enhanced_prompt
    
    def translate_chunk(
        self, 
        chunk: ChunkInfo, 
        source_lang: str = "auto", 
        target_lang: str = "ja"
    ) -> TranslationResult:
        """Translate a single chunk with context."""
        try:
            # Get context summary
            context_summary = self.context.get_summary()
            
            # Create enhanced system prompt
            system_prompt = self.get_enhanced_system_prompt(
                source_lang, target_lang, context_summary
            )
            
            # Prepare translation request
            prepared_text = self.base_translator.prepare_text(chunk.text)
            
            # For Ollama translator, we need to modify the request
            if hasattr(self.base_translator, 'translator_config'):
                payload = {
                    "model": self.base_translator.translator_config.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prepared_text},
                    ],
                    "stream": False,
                    "temperature": self.base_translator.translator_config.temperature,
                    "max_tokens": self.base_translator.translator_config.max_tokens,
                }
                
                # Make request directly
                import requests
                url = f"{self.base_translator.translator_config.base_url}/v1/chat/completions"
                response = requests.post(
                    url, 
                    json=payload, 
                    timeout=self.base_translator.translator_config.timeout
                )
                response.raise_for_status()
                
                result_data = response.json()
                translated_text = result_data["choices"][0]["message"]["content"]
                
                result = TranslationResult(
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    success=True,
                    metadata={
                        "model": self.base_translator.translator_config.model,
                        "engine": "ollama",
                        "chunk_id": chunk.chunk_id,
                        "context_used": bool(context_summary)
                    }
                )
            else:
                # Fallback to base translator
                result = self.base_translator.translate(chunk.text, source_lang, target_lang)
                result.metadata.update({
                    "chunk_id": chunk.chunk_id,
                    "context_used": bool(context_summary)
                })
            
            # Update context if successful
            if result.success:
                self.context.previous_chunks.append(result.translated_text[:200])
                # Extract terminology (simple pattern matching)
                self._extract_terminology(chunk.text, result.translated_text)
            
            return result
            
        except Exception as e:
            logger.error(f"Chunk translation failed: {str(e)}")
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                success=False,
                error=str(e),
                metadata={"chunk_id": chunk.chunk_id}
            )
    
    def translate_chunked(
        self, 
        text: str, 
        source_lang: str = "auto", 
        target_lang: str = "ja"
    ) -> List[TranslationResult]:
        """Translate text in chunks with context preservation."""
        logger.debug(f"Starting chunked translation (text length: {len(text)})")
        
        # Reset context for new translation
        self.context = TranslationContext()
        
        # Split into chunks
        chunks = self.chunker.chunk_text(text)
        logger.debug(f"Split into {len(chunks)} chunks")
        
        results = []
        for i, chunk in enumerate(chunks):
            progress = (i+1) / len(chunks) * 100
            logger.info(f"🔧 Translating chunk {i+1}/{len(chunks)} ({progress:.1f}%) - {len(chunk.text)} chars")
            
            chunk_start = time.time()
            
            result = self.translate_chunk(chunk, source_lang, target_lang)
            results.append(result)
            
            chunk_duration = time.time() - chunk_start
            
            if result.success:
                logger.info(f"✅ Chunk {i+1} completed in {chunk_duration:.1f}s")
            else:
                logger.error(f"❌ Chunk {i+1} failed after {chunk_duration:.1f}s: {result.error}")
                # Continue with next chunk even if one fails
            
        return results
    
    def _extract_terminology(self, source_text: str, translated_text: str) -> None:
        """Extract terminology patterns from source and translated text."""
        # Simple pattern matching for technical terms
        # Look for terms in parentheses in translated text like "翻訳語（original）"
        pattern = r'([^（]+)（([^）]+)）'
        matches = re.findall(pattern, translated_text)
        
        for translated_term, original_term in matches:
            if original_term in source_text:
                self.context.terminology[original_term.strip()] = translated_term.strip()
    
    def merge_translation_results(self, results: List[TranslationResult]) -> str:
        """Merge chunked translation results into single text."""
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return ""
        
        # Simple merge - join with double newlines to preserve paragraph structure
        merged_text = "\n\n".join([r.translated_text for r in successful_results])
        
        # Remove overlap duplicates (basic implementation)
        # This could be more sophisticated
        return merged_text