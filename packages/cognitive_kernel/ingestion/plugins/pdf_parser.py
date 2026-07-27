from typing import Any, List, Dict
import pdfplumber
import io
from ..parser import BaseParser, PARSER_REGISTRY

class PDFParser(BaseParser):
    def parse(self, file_content: bytes) -> Dict[str, Any]:
        text = ""
        metadata = {}
        with io.BytesIO(file_content) as f:
            with pdfplumber.open(f) as pdf:
                metadata["total_pages"] = len(pdf.pages)
                for page in pdf.pages:
                    text += page.extract_text()
        return {"text": text, "metadata": metadata}

    def extract_content(self, parsed_data: Dict[str, Any]) -> str:
        return parsed_data.get("text", "")

    def extract_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        return parsed_data.get("metadata", {})

    def extract_entities(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def extract_relationships(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def validate(self, parsed_data: Dict[str, Any]) -> bool:
        return "text" in parsed_data

def initialize():
    PARSER_REGISTRY.register_parser(".pdf", PDFParser())

initialize()
