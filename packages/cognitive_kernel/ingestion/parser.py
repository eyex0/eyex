from abc import ABC, abstractmethod
from typing import Any, List, Dict

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_content: bytes) -> Dict[str, Any]:
        ...

    @abstractmethod
    def extract_content(self, parsed_data: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    def extract_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def extract_entities(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def extract_relationships(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def validate(self, parsed_data: Dict[str, Any]) -> bool:
        ...

class ParserRegistry:
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}

    def register_parser(self, file_extension: str, parser: BaseParser):
        self._parsers[file_extension] = parser

    def get_parser(self, file_extension: str) -> BaseParser | None:
        return self._parsers.get(file_extension)

    def list_parsers(self) -> List[str]:
        return list(self._parsers.keys())

PARSER_REGISTRY = ParserRegistry()
