from __future__ import annotations

import csv
import io
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("pix.services.connectors")


@dataclass
class ConnectorDocument:
    id: str
    filename: str
    content: str
    mime_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)
    chunks: list[str] = field(default_factory=list)


class BaseConnector(ABC):
    @abstractmethod
    async def fetch(self, source: str, **kwargs: Any) -> list[ConnectorDocument]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class FileUploadConnector(BaseConnector):
    """Processes uploaded files (CSV, TXT, JSON, MD)."""

    CHUNK_SIZE = 500

    def name(self) -> str:
        return "file_upload"

    async def fetch(self, source: str, **kwargs: Any) -> list[ConnectorDocument]:
        ext = Path(source).suffix.lower()
        content = kwargs.get("content", b"")
        if not content:
            return []

        doc_id = kwargs.get("doc_id", f"file_{os.urandom(4).hex()}")
        filename = Path(source).name

        if ext == ".csv":
            text = self._parse_csv(content)
        elif ext == ".json":
            text = self._parse_json(content)
        else:
            text = content.decode("utf-8", errors="replace")

        chunks = self._chunk_text(text)

        return [ConnectorDocument(
            id=doc_id,
            filename=filename,
            content=text,
            mime_type=self._mime_for(ext),
            metadata={"source": "upload", "ext": ext},
            chunks=chunks,
        )]

    def _parse_csv(self, content: bytes) -> str:
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            rows = []
            for row in reader:
                rows.append(json.dumps(row))
            return "\n".join(rows) if rows else content.decode("utf-8", errors="replace")
        except Exception:
            return content.decode("utf-8", errors="replace")

    def _parse_json(self, content: bytes) -> str:
        try:
            data = json.loads(content)
            return json.dumps(data, indent=2)
        except Exception:
            return content.decode("utf-8", errors="replace")

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        return [" ".join(words[i:i + self.CHUNK_SIZE]) for i in range(0, len(words), self.CHUNK_SIZE)]

    @staticmethod
    def _mime_for(ext: str) -> str:
        return {
            ".csv": "text/csv",
            ".json": "application/json",
            ".md": "text/markdown",
            ".txt": "text/plain",
        }.get(ext, "text/plain")


class ApiConnector(BaseConnector):
    """Connects to external REST APIs to fetch business data."""

    def name(self) -> str:
        return "api"

    async def fetch(self, source: str, **kwargs: Any) -> list[ConnectorDocument]:
        from httpx import AsyncClient

        headers = kwargs.get("headers", {})
        params = kwargs.get("params", {})

        async with AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(source, headers=headers, params=params)
                resp.raise_for_status()
                text = resp.text
                doc_id = kwargs.get("doc_id", f"api_{os.urandom(4).hex()}")
                return [ConnectorDocument(
                    id=doc_id,
                    filename=f"api_{urlparse(source).netloc}.json",
                    content=text[:100000],
                    mime_type="application/json",
                    metadata={"source": "api", "url": source, "status": resp.status_code},
                    chunks=self._chunk_text(text[:100000]),
                )]
            except Exception as exc:
                logger.warning("API connector failed for %s: %s", source, exc)
                return []

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        chunk_size = 500
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


class DatabaseConnector(BaseConnector):
    """Connects to business databases (PostgreSQL, MySQL, SQLite)."""

    def name(self) -> str:
        return "database"

    async def fetch(self, source: str, **kwargs: Any) -> list[ConnectorDocument]:
        from sqlalchemy import create_engine
        from sqlalchemy import text as sa_text

        query = kwargs.get("query", "SELECT * FROM information_schema.tables LIMIT 100")
        connection_string = source

        try:
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                result = conn.execute(sa_text(query))
                rows = [dict(row._mapping) for row in result]

            text = json.dumps(rows, indent=2, default=str)
            doc_id = kwargs.get("doc_id", f"db_{os.urandom(4).hex()}")
            return [ConnectorDocument(
                id=doc_id,
                filename=f"db_query_{query[:30]}.json",
                content=text[:100000],
                mime_type="application/json",
                metadata={"source": "database", "rows": len(rows)},
                chunks=self._chunk_text(text[:100000]),
            )]
        except Exception as exc:
            logger.warning("Database connector failed: %s", exc)
            return []

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        chunk_size = 500
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


class ConnectorRegistry:
    """Central registry for all data connectors."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {
            "file": FileUploadConnector(),
            "api": ApiConnector(),
            "database": DatabaseConnector(),
        }

    def list_types(self) -> list[str]:
        return list(self._connectors.keys())

    def get(self, connector_type: str) -> BaseConnector | None:
        return self._connectors.get(connector_type)

    async def fetch_and_store(
        self,
        connector_type: str,
        source: str,
        org_id: str = "default",
        **kwargs: Any,
    ) -> list[ConnectorDocument]:
        connector = self.get(connector_type)
        if not connector:
            logger.warning("Unknown connector type: %s", connector_type)
            return []

        documents = await connector.fetch(source, **kwargs)
        if not documents:
            return []

        from packages.cognitive_kernel.knowledge_graph import get_knowledge_graph
        from packages.cognitive_kernel.memory_engine import get_vector_memory
        kg = get_knowledge_graph()
        vm = get_vector_memory()

        for doc in documents:
            vm.store(
                text=doc.content[:2000],
                metadata={"filename": doc.filename, "source": connector_type, "org_id": org_id},
                source=connector_type,
                org_id=org_id,
                entry_id=doc.id,
            )

            for i, chunk in enumerate(doc.chunks):
                chunk_id = f"{doc.id}_chunk_{i}"
                vm.store(
                    text=chunk,
                    metadata={"filename": doc.filename, "chunk_index": i, "org_id": org_id},
                    source=connector_type,
                    org_id=org_id,
                    entry_id=chunk_id,
                )

            kg.add_node(
                node_id=f"doc_{doc.id}",
                label=doc.filename,
                node_type="document",
                properties={"source": connector_type, "chunks": len(doc.chunks)},
                org_id=org_id,
            )

        logger.info("Stored %d documents from connector '%s' for org=%s", len(documents), connector_type, org_id)
        return documents


_registry: ConnectorRegistry | None = None


def get_connector_registry() -> ConnectorRegistry:
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
    return _registry
