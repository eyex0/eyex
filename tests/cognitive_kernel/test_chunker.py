"""Tests for the TextChunker."""
import pytest
from packages.cognitive_kernel.memory_engine.chunker import TextChunker


class TestTextChunker:
    def setup_method(self):
        self.chunker = TextChunker()
        self.sample_text = "This is sentence one. This is sentence two. " * 20

    def test_chunk_fixed_size(self):
        chunks = self.chunker.chunk_fixed_size(self.sample_text, size=100, overlap=20)
        assert len(chunks) > 1
        assert all("text" in c and "id" in c and "token_count" in c for c in chunks)
        assert all(c["start_pos"] < c["end_pos"] for c in chunks)

    def test_chunk_sliding_window(self):
        chunks = self.chunker.chunk_sliding_window(self.sample_text, window=100, step=50)
        assert len(chunks) > 1
        # Verify overlap: second chunk starts before first ends
        if len(chunks) >= 2:
            assert chunks[1]["start_pos"] < chunks[0]["end_pos"]

    def test_chunk_semantic(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = self.chunker.chunk_semantic(text)
        assert len(chunks) == 3
        assert "Paragraph one" in chunks[0]["text"]
        assert "Paragraph two" in chunks[1]["text"]

    def test_chunk_recursive_short_text(self):
        text = "Short text."
        chunks = self.chunker.chunk_recursive(text, max_size=512, min_size=10)
        assert len(chunks) == 1

    def test_chunk_recursive_long_text(self):
        text = "This is a paragraph. " * 100
        chunks = self.chunker.chunk_recursive(text, max_size=100, min_size=20)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c["text"]) <= 200  # Allow some flexibility

    def test_token_count(self):
        count = TextChunker._count_tokens("hello world test")
        assert count == 4  # 3 words * 1.3 ≈ 3.9, rounded to 4

    def test_empty_text(self):
        chunks = self.chunker.chunk_fixed_size("", size=100, overlap=20)
        assert chunks == []
