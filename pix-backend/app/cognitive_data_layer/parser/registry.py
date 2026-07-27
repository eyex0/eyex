from __future__ import annotations

import mimetypes
from pathlib import Path

from app.cognitive_data_layer.parser.base import BaseParser, ParseResult


class ParserRegistry:
    """Registry for parser plugins."""

    def __init__(self) -> None:
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser) -> None:
        self._parsers.append(parser)

    def unregister(self, parser: BaseParser) -> None:
        self._parsers.remove(parser)

    def get_parser(self, source: str | Path | bytes, hint: str | None = None) -> BaseParser | None:
        if hint:
            for parser in self._parsers:
                if hint.lower() in parser.name.lower() or hint.lower() in [
                    ext.lower().lstrip(".") for ext in parser.supported_extensions
                ]:
                    return parser
        for parser in self._parsers:
            if parser.can_parse(source):
                return parser
        return None

    async def parse(
        self, source: str | Path | bytes, options: dict | None = None, hint: str | None = None
    ) -> ParseResult:
        parser = self.get_parser(source, hint=hint)
        if not parser:
            source_repr = source if isinstance(source, (str, Path)) else "<bytes>"
            raise ValueError(f"No parser found for source: {source_repr}")
        return await parser.parse(source, options=options or {})

    def list_parsers(self) -> list[str]:
        return [p.name for p in self._parsers]


def _get_extension(source: str | Path | bytes) -> str:
    if isinstance(source, (str, Path)):
        return Path(source).suffix.lower().lstrip(".")
    return ""


def _get_mime_type(source: str | Path | bytes) -> str:
    if isinstance(source, (str, Path)):
        mime, _ = mimetypes.guess_type(str(source))
        return mime or ""
    return ""


# Global registry instance
_parser_registry: ParserRegistry | None = None


def get_parser_registry() -> ParserRegistry:
    global _parser_registry
    if _parser_registry is None:
        _parser_registry = ParserRegistry()
    return _parser_registry


def register_parser(parser: BaseParser) -> None:
    get_parser_registry().register(parser)


async def parse_source(
    source: str | Path | bytes, options: dict | None = None, hint: str | None = None
) -> ParseResult:
    return await get_parser_registry().parse(source, options=options, hint=hint)
