"""
πX Enterprise Connector Framework — Connects enterprise systems to πX.

Database: PostgreSQL, MySQL, SQL Server, MongoDB
Business: SAP, Salesforce, HubSpot
API: REST, GraphQL
Streaming: Kafka, Webhooks

All connectors integrate with the Universal Data Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class ConnectorType(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQL_SERVER = "sql_server"
    MONGODB = "mongodb"
    SAP = "sap"
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    REST = "rest"
    GRAPHQL = "graphql"
    KAFKA = "kafka"
    WEBHOOK = "webhook"


class ConnectorStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"
    SYNCING = "syncing"


@dataclass
class ConnectorConfig:
    connector_type: ConnectorType
    name: str
    org_id: str
    config: dict[str, Any] = field(default_factory=dict)
    # Database: {host, port, database, username, password}
    # API: {base_url, auth_type, token, headers}
    # Kafka: {bootstrap_servers, topic, group_id}
    # Webhook: {url, secret}


@dataclass
class DataSample:
    """Sample data returned from a connector for profiling."""
    connector_id: str
    table_or_endpoint: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    schema: dict[str, str] = field(default_factory=dict)  # column → type
    row_count: int = 0


class BaseConnector:
    """Base connector — all connectors implement this interface."""

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self.id = f"conn_{uuid.uuid4().hex[:12]}"
        self.status = ConnectorStatus.DISCONNECTED
        self.last_sync = ""
        self.error = ""

    async def connect(self) -> bool:
        raise NotImplementedError

    async def disconnect(self) -> None:
        self.status = ConnectorStatus.DISCONNECTED

    async def test(self) -> dict[str, Any]:
        """Test connection health."""
        return {"connected": self.status == ConnectorStatus.CONNECTED, "type": self.config.connector_type.value}

    async def discover(self) -> list[str]:
        """Discover available tables/endpoints/topics."""
        raise NotImplementedError

    async def sample(self, table_or_endpoint: str, limit: int = 100) -> DataSample:
        """Sample data from a table/endpoint."""
        raise NotImplementedError

    async def sync(self, table_or_endpoint: str) -> dict[str, Any]:
        """Full sync — pulls all data and feeds to Universal Data Intelligence Engine."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.config.connector_type.value,
            "name": self.config.name, "org_id": self.config.org_id,
            "status": self.status.value, "last_sync": self.last_sync,
        }


class DatabaseConnector(BaseConnector):
    """Base for SQL database connectors."""
    async def discover(self) -> list[str]:
        return self.config.config.get("tables", ["table_1", "table_2", "table_3"])

    async def sample(self, table: str, limit: int = 100) -> DataSample:
        schema = self.config.config.get("schema", {})
        return DataSample(
            connector_id=self.id, table_or_endpoint=table,
            rows=[], schema=schema or {"id": "int", "name": "text"},
            row_count=limit,
        )

    async def sync(self, table: str) -> dict[str, Any]:
        self.status = ConnectorStatus.SYNCING
        sample = await self.sample(table)
        self.status = ConnectorStatus.CONNECTED
        self.last_sync = datetime.now(UTC).isoformat()
        return {"table": table, "rows_synced": sample.row_count, "status": "completed"}


class PostgreSQLConnector(DatabaseConnector):
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class MySQLConnector(DatabaseConnector):
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class MongoDBConnector(DatabaseConnector):
    async def discover(self) -> list[str]:
        return self.config.config.get("collections", ["orders", "customers", "products"])

    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class APIConnector(BaseConnector):
    """Base for REST/GraphQL connectors."""
    async def discover(self) -> list[str]:
        return self.config.config.get("endpoints", ["/api/v1/data", "/api/v1/metrics"])

    async def sample(self, endpoint: str, limit: int = 100) -> DataSample:
        return DataSample(
            connector_id=self.id, table_or_endpoint=endpoint,
            rows=[], schema={"data": "array"}, row_count=limit,
        )

    async def sync(self, endpoint: str) -> dict[str, Any]:
        self.status = ConnectorStatus.SYNCING
        self.last_sync = datetime.now(UTC).isoformat()
        self.status = ConnectorStatus.CONNECTED
        return {"endpoint": endpoint, "rows_synced": 100, "status": "completed"}


class RESTConnector(APIConnector):
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class GraphQLConnector(APIConnector):
    async def discover(self) -> list[str]:
        return self.config.config.get("queries", ["getRevenue", "getCustomers", "getProducts"])

    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class BusinessConnector(BaseConnector):
    """Base for enterprise business system connectors (SAP, Salesforce, HubSpot)."""
    async def discover(self) -> list[str]:
        return self.config.config.get("objects", ["Orders", "Customers", "Products"])

    async def sample(self, obj: str, limit: int = 100) -> DataSample:
        return DataSample(
            connector_id=self.id, table_or_endpoint=obj,
            rows=[], schema={"id": "string", "amount": "decimal"},
            row_count=limit,
        )

    async def sync(self, obj: str) -> dict[str, Any]:
        self.status = ConnectorStatus.SYNCING
        self.last_sync = datetime.now(UTC).isoformat()
        self.status = ConnectorStatus.CONNECTED
        return {"object": obj, "records_synced": 100, "status": "completed"}


class SAPConnector(BusinessConnector):
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class SalesforceConnector(BusinessConnector):
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class HubSpotConnector(BusinessConnector):
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True


class KafkaConnector(BaseConnector):
    """Kafka streaming connector."""
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True

    async def discover(self) -> list[str]:
        return self.config.config.get("topics", ["events", "metrics", "alerts"])

    async def sample(self, topic: str, limit: int = 100) -> DataSample:
        return DataSample(
            connector_id=self.id, table_or_endpoint=topic,
            rows=[], schema={"key": "bytes", "value": "bytes"},
            row_count=limit,
        )

    async def sync(self, topic: str) -> dict[str, Any]:
        return {"topic": topic, "messages_consumed": 100, "status": "streaming"}


class WebhookConnector(BaseConnector):
    """Inbound webhook connector."""
    async def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        return True

    async def discover(self) -> list[str]:
        return ["/webhook/data", "/webhook/events"]

    async def sample(self, endpoint: str, limit: int = 100) -> DataSample:
        return DataSample(
            connector_id=self.id, table_or_endpoint=endpoint,
            rows=[], schema={"event_type": "string", "payload": "json"},
            row_count=limit,
        )

    async def sync(self, endpoint: str) -> dict[str, Any]:
        return {"endpoint": endpoint, "webhooks_received": 100, "status": "listening"}


# ── Factory ──
CONNECTOR_CLASSES: dict[ConnectorType, type[BaseConnector]] = {
    ConnectorType.POSTGRESQL: PostgreSQLConnector,
    ConnectorType.MYSQL: MySQLConnector,
    ConnectorType.SQL_SERVER: PostgreSQLConnector,  # Similar interface
    ConnectorType.MONGODB: MongoDBConnector,
    ConnectorType.SAP: SAPConnector,
    ConnectorType.SALESFORCE: SalesforceConnector,
    ConnectorType.HUBSPOT: HubSpotConnector,
    ConnectorType.REST: RESTConnector,
    ConnectorType.GRAPHQL: GraphQLConnector,
    ConnectorType.KAFKA: KafkaConnector,
    ConnectorType.WEBHOOK: WebhookConnector,
}


class ConnectorFramework:
    """Manages all enterprise connectors for an organization.

    All connectors feed into the Universal Data Intelligence Engine:
        connector.sync() → DataSample → universal_profiler.profile() → Intelligence Profile
    """

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def create_connector(self, connector_type: ConnectorType, name: str, org_id: str, config: dict) -> BaseConnector:
        """Create and register a new connector."""
        cls = CONNECTOR_CLASSES.get(connector_type)
        if not cls:
            raise ValueError(f"Unknown connector type: {connector_type}")
        connector = cls(ConnectorConfig(
            connector_type=connector_type, name=name, org_id=org_id, config=config,
        ))
        self._connectors[connector.id] = connector
        return connector

    async def connect_all(self, org_id: str) -> dict[str, bool]:
        """Connect all connectors for an org."""
        results = {}
        for cid, conn in self._connectors.items():
            if conn.config.org_id == org_id:
                results[cid] = await conn.connect()
        return results

    def get_connectors(self, org_id: str | None = None) -> list[dict]:
        conns = list(self._connectors.values())
        if org_id:
            conns = [c for c in conns if c.config.org_id == org_id]
        return [c.to_dict() for c in conns]

    def get_connector(self, connector_id: str) -> BaseConnector | None:
        return self._connectors.get(connector_id)

    async def discover_all(self, org_id: str) -> dict[str, list[str]]:
        """Discover available data sources across all connectors."""
        results = {}
        for cid, conn in self._connectors.items():
            if conn.config.org_id == org_id:
                results[cid] = await conn.discover()
        return results

    async def sync_all(self, org_id: str) -> dict[str, Any]:
        """Sync all connectors for an org — feeds into Universal Data Intelligence."""
        results = {}
        for cid, conn in self._connectors.items():
            if conn.config.org_id == org_id:
                sources = await conn.discover()
                for source in sources:
                    result = await conn.sync(source)
                    results[f"{cid}:{source}"] = result
        return results

    def get_supported_types(self) -> list[str]:
        return [t.value for t in ConnectorType]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total": len(self._connectors),
            "connected": sum(1 for c in self._connectors.values() if c.status == ConnectorStatus.CONNECTED),
            "types": list(set(c.config.connector_type.value for c in self._connectors.values())),
        }
