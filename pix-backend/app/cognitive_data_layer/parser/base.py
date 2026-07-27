from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ParseResult:
    raw_data: Any
    format: str
    metadata: dict
    warnings: list[str]


class BaseParser(ABC):
    """Base class for all data parsers."""

    name: str = ""
    supported_extensions: list[str] = []

    @abstractmethod
    def can_parse(self, source: str | Path | bytes, hint: str | None = None) -> bool:
        """Return True if this parser can handle the source."""

    @abstractmethod
    async def parse(self, source: str | Path | bytes, options: dict | None = None) -> ParseResult:
        """Parse source into a raw representation."""


class ParserPlugin(BaseParser):
    """Alias for BaseParser used by the plugin registry."""
