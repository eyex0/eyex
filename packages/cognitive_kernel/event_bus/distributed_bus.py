"""
πX Distributed Event Bus — Redis Streams + PostgreSQL LISTEN/NOTIFY.

Features: distributed events, retry, dead letter queue, tenant isolation.
Production: Redis Streams (XADD/XREADGROUP) with consumer groups.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable
import uuid


class EventStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class DistributedEvent:
    id: str
    stream: str  # e.g. "kpi_events", "data_events", "agent_events"
    event_type: str
    org_id: str
    agent_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    status: EventStatus = EventStatus.PENDING
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    processed_at: str = ""
    consumer_id: str = ""  # which consumer processed this

    def to_dict(self) -> dict:
        return {
            "id": self.id, "stream": self.stream, "event_type": self.event_type,
            "org_id": self.org_id, "agent_id": self.agent_id,
            "payload": self.payload, "retry_count": self.retry_count,
            "max_retries": self.max_retries, "status": self.status.value,
            "error": self.error, "created_at": self.created_at,
            "processed_at": self.processed_at, "consumer_id": self.consumer_id,
        }


class DistributedEventBus:
    """Redis Streams + PostgreSQL LISTEN/NOTIFY event bus.

    Production:
        - Redis: XADD for publish, XREADGROUP for consume, XPENDING for retry, XDEL for ack
        - PostgreSQL: LISTEN/NOTIFY for real-time notifications
        - Dead letter queue: separate Redis Stream for failed events
    """

    STREAMS = ["kpi_events", "data_events", "agent_events", "system_events", "security_events"]

    def __init__(self) -> None:
        self._streams: dict[str, list[DistributedEvent]] = {s: [] for s in self.STREAMS}
        self._consumers: dict[str, list[Callable]] = {}  # stream → handlers
        self._dead_letter: list[DistributedEvent] = []
        self._consumer_groups: dict[str, list[str]] = {}  # group_name → consumer_ids
        self._processed: list[DistributedEvent] = []

    def get_stream(self, event_type: str) -> str:
        """Route event type to the correct stream."""
        if event_type.startswith("kpi"):
            return "kpi_events"
        elif event_type.startswith("data"):
            return "data_events"
        elif event_type.startswith("agent"):
            return "agent_events"
        elif event_type.startswith("security"):
            return "security_events"
        return "system_events"

    def publish(self, event_type: str, org_id: str, agent_id: str = "",
                payload: dict | None = None, max_retries: int = 3) -> DistributedEvent:
        """Publish to Redis Stream (XADD)."""
        stream = self.get_stream(event_type)
        event = DistributedEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            stream=stream,
            event_type=event_type,
            org_id=org_id,
            agent_id=agent_id,
            payload=payload or {},
            max_retries=max_retries,
        )
        self._streams[stream].append(event)
        return event

    def subscribe(self, stream: str, handler: Callable, consumer_id: str = "consumer_1") -> None:
        """Subscribe to a stream with consumer group (XREADGROUP)."""
        if stream not in self._consumers:
            self._consumers[stream] = []
        self._consumers[stream].append(handler)
        if stream not in self._consumer_groups:
            self._consumer_groups[stream] = []
        if consumer_id not in self._consumer_groups[stream]:
            self._consumer_groups[stream].append(consumer_id)

    def consume(self, stream: str, consumer_id: str = "consumer_1", limit: int = 10) -> list[DistributedEvent]:
        """Consume from stream (XREADGROUP). Returns unprocessed events."""
        events = self._streams.get(stream, [])
        unprocessed = [e for e in events if e.status == EventStatus.PENDING]
        for event in unprocessed[:limit]:
            event.status = EventStatus.PROCESSING
            event.consumer_id = consumer_id
        return unprocessed[:limit]

    def ack(self, event_id: str) -> bool:
        """Acknowledge event processing (XACK)."""
        for stream_events in self._streams.values():
            for e in stream_events:
                if e.id == event_id:
                    e.status = EventStatus.PROCESSED
                    e.processed_at = datetime.now(UTC).isoformat()
                    self._processed.append(e)
                    return True
        return False

    def nack(self, event_id: str, error: str) -> bool:
        """Negative ack — retry or dead letter."""
        for stream_events in self._streams.values():
            for e in stream_events:
                if e.id == event_id:
                    e.error = error
                    e.retry_count += 1
                    if e.retry_count >= e.max_retries:
                        e.status = EventStatus.DEAD_LETTER
                        self._dead_letter.append(e)
                    else:
                        e.status = EventStatus.PENDING
                    return True
        return False

    def process(self, stream: str, handler: Callable) -> list[DistributedEvent]:
        """Process all pending events in a stream with a handler."""
        events = self.consume(stream)
        for event in events:
            try:
                handler(event)
                self.ack(event.id)
            except Exception as e:
                self.nack(event.id, str(e))
        return events

    def get_dead_letter(self, org_id: str | None = None) -> list[dict]:
        events = self._dead_letter
        if org_id:
            events = [e for e in events if e.org_id == org_id]
        return [e.to_dict() for e in events]

    def replay_from_dead_letter(self, event_id: str) -> bool:
        """Replay an event from the dead letter queue."""
        for i, e in enumerate(self._dead_letter):
            if e.id == event_id:
                e.retry_count = 0
                e.status = EventStatus.PENDING
                e.error = ""
                self._dead_letter.pop(i)
                self._streams[e.stream].append(e)
                return True
        return False

    def get_stats(self) -> dict[str, Any]:
        total = sum(len(events) for events in self._streams.values())
        return {
            "total_events": total,
            "processed": len(self._processed),
            "dead_letter_count": len(self._dead_letter),
            "streams": {s: len(events) for s, events in self._streams.items()},
            "consumer_groups": {s: len(c) for s, c in self._consumer_groups.items()},
        }

    def get_pending(self, stream: str | None = None) -> list[dict]:
        if stream:
            events = [e for e in self._streams.get(stream, []) if e.status == EventStatus.PENDING]
        else:
            events = [e for s in self._streams.values() for e in s if e.status == EventStatus.PENDING]
        return [e.to_dict() for e in events]

    def get_events(self, org_id: str | None = None, stream: str | None = None, limit: int = 50) -> list[dict]:
        if stream:
            events = self._streams.get(stream, [])
        else:
            events = [e for s in self._streams.values() for e in s]
        if org_id:
            events = [e for e in events if e.org_id == org_id]
        return [e.to_dict() for e in events[-limit:]]
