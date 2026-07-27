"""πX Text Normalizer — Clean and normalize text for ingestion."""
from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    """Normalizes and cleans text before chunking and embedding."""

    @staticmethod
    def normalize(text: str) -> str:
        """Fix encoding, remove BOM, normalize whitespace."""
        # Remove BOM
        text = text.replace('\ufeff', '')
        # Normalize unicode
        text = unicodedata.normalize('NFKC', text)
        # Strip
        text = text.strip()
        # Normalize whitespace (collapse multiple spaces/newlines)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    @staticmethod
    def clean(text: str) -> str:
        """Remove HTML tags, fix smart quotes, normalize dashes."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Smart quotes to straight
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        # Em/en dashes
        text = text.replace('\u2013', '-').replace('\u2014', '-')
        # Non-breaking spaces
        text = text.replace('\u00a0', ' ')
        return text

    @staticmethod
    def extract_structure(text: str) -> dict:
        """Extract structural elements from text."""
        lines = text.split('\n')
        headings = []
        paragraphs = []
        lists = []
        current_para = []

        for line in lines:
            stripped = line.strip()
            # Headings (markdown or all-caps short lines)
            if re.match(r'^#{1,6}\s+', stripped):
                headings.append(stripped)
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
            elif re.match(r'^[-*•]\s+', stripped):
                lists.append(stripped)
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
            elif stripped:
                current_para.append(line)
            else:
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []

        if current_para:
            paragraphs.append('\n'.join(current_para))

        return {
            "headings": headings,
            "paragraphs": paragraphs,
            "lists": lists,
        }
