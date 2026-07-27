"""πX Text Chunker — Multiple chunking strategies for the memory engine."""
from __future__ import annotations

import uuid
from enum import Enum


class ChunkingStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    SLIDING_WINDOW = "sliding_window"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


class TextChunker:
    """Chunks text into smaller pieces for embedding and storage."""

    @staticmethod
    def _count_tokens(text: str) -> int:
        return max(1, int(len(text.split()) * 1.3))

    @staticmethod
    def _make_chunk(text: str, idx: int, start: int, end: int) -> dict:
        return {
            "id": f"chunk_{uuid.uuid4().hex[:8]}",
            "text": text[start:end].strip(),
            "start_pos": start,
            "end_pos": end,
            "token_count": TextChunker._count_tokens(text[start:end]),
            "chunk_index": idx,
        }

    @staticmethod
    def chunk_fixed_size(text: str, size: int = 512, overlap: int = 50) -> list[dict]:
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(TextChunker._make_chunk(text, idx, start, end))
            start = end - overlap if end < len(text) else end
            idx += 1
        return chunks

    @staticmethod
    def chunk_sliding_window(text: str, window: int = 512, step: int = 256) -> list[dict]:
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + window, len(text))
            chunks.append(TextChunker._make_chunk(text, idx, start, end))
            start += step
            idx += 1
        return chunks

    @staticmethod
    def chunk_semantic(text: str) -> list[dict]:
        """Split on paragraph boundaries and headings."""
        import re
        # Split on double newlines (paragraphs) and markdown headings
        parts = re.split(r'\n\n+|(?=^#{1,6}\s)', text, flags=re.MULTILINE)
        chunks = []
        pos = 0
        for idx, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            start = text.find(part, pos)
            end = start + len(part)
            pos = end
            chunks.append(TextChunker._make_chunk(text, idx, start, end))
        return chunks

    @staticmethod
    def chunk_recursive(text: str, max_size: int = 512, min_size: int = 100) -> list[dict]:
        """Recursive character splitting — try paragraphs, then sentences, then words."""
        if len(text) <= max_size:
            return [TextChunker._make_chunk(text, 0, 0, len(text))]

        # Try paragraph splits first
        import re
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current = ""
        current_start = 0
        pos = 0
        idx = 0

        for para in paragraphs:
            if len(current) + len(para) + 2 <= max_size:
                current = current + "\n\n" + para if current else para
            else:
                if current and len(current) >= min_size:
                    start = text.find(current, current_start)
                    end = start + len(current)
                    chunks.append(TextChunker._make_chunk(text, idx, start, end))
                    idx += 1
                    current_start = end
                # If para itself is too long, split by sentences
                if len(para) > max_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    for sent in sentences:
                        if len(current) + len(sent) + 1 <= max_size:
                            current = current + " " + sent if current else sent
                        else:
                            if current and len(current) >= min_size:
                                start = text.find(current, current_start)
                                end = start + len(current)
                                chunks.append(TextChunker._make_chunk(text, idx, start, end))
                                idx += 1
                                current_start = end
                                current = ""
                            current = sent
                else:
                    current = para
        if current and len(current) >= min_size:
            start = text.find(current, current_start)
            end = start + len(current)
            chunks.append(TextChunker._make_chunk(text, idx, start, end))
        return chunks
