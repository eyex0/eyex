"""Cross-database type compatibility for PostgreSQL + SQLite."""
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class JSONBCompat(TypeDecorator):
    """JSONB on PostgreSQL, JSON on SQLite — stores JSON everywhere."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
