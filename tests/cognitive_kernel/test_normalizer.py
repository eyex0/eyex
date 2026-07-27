"""Tests for the TextNormalizer."""
from packages.cognitive_kernel.memory_engine.normalizer import TextNormalizer


class TestTextNormalizer:
    def setup_method(self):
        self.normalizer = TextNormalizer()

    def test_normalize_bom(self):
        text = "\ufeffHello world"
        result = self.normalizer.normalize(text)
        assert not result.startswith("\ufeff")
        assert result == "Hello world"

    def test_normalize_whitespace(self):
        text = "Hello    world\n\n\n\nGoodbye"
        result = self.normalizer.normalize(text)
        assert "    " not in result
        assert "\n\n\n" not in result

    def test_clean_html(self):
        text = "<p>Hello <b>world</b></p>"
        result = self.normalizer.clean(text)
        assert "<" not in result
        assert "Hello world" in result

    def test_clean_smart_quotes(self):
        text = "\u201cHello\u201d \u2018world\u2019"
        result = self.normalizer.clean(text)
        assert '"' in result
        assert "'" in result

    def test_extract_structure(self):
        text = "# Heading 1\n\nParagraph one.\n\n## Heading 2\n\n- Item 1\n- Item 2"
        result = self.normalizer.extract_structure(text)
        assert len(result["headings"]) == 2
        assert len(result["paragraphs"]) >= 1
        assert len(result["lists"]) == 2
