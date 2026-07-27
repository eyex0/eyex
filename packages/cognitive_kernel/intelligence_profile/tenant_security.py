"""
πX Tenant Security Guard — Enforces tenant isolation boundaries.

Every query against profile tables MUST be scoped to organization_id.
This module provides guard rails to prevent cross-tenant data leakage.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.tenant_security")

# Tables that contain organization-scoped data
TENANT_TABLES = [
    "intelligence_profiles",
    "profile_versions",
    "profile_ontology",
    "profile_kpis",
    "profile_glossary",
    "profile_data_sources",
    "profile_events",
    "profile_semantic_history",
]


class ProfileTenantGuard:
    """Enforces tenant isolation for intelligence profile operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def verify_access(
        self,
        organization_id: str,
        profile_id: str,
        required_status: str | None = None,
    ) -> bool:
        """Verify that a profile belongs to the given organization."""
        async with self.session_factory() as db:
            query = text(
                "SELECT id, status FROM intelligence_profiles "
                "WHERE id = :pid AND organization_id = :org_id"
            )
            result = await db.execute(query, {"pid": profile_id, "org_id": organization_id})
            row = result.fetchone()
            if not row:
                logger.warning(
                    "Access denied: profile %s not found for org %s", profile_id, organization_id
                )
                return False
            if required_status and row[1] != required_status:
                logger.warning(
                    "Access denied: profile %s has status '%s', required '%s'",
                    profile_id, row[1], required_status,
                )
                return False
            return True

    async def verify_entity_ownership(
        self,
        organization_id: str,
        table_name: str,
        entity_id: str,
    ) -> bool:
        """Verify that an entity belongs to the given organization."""
        if table_name not in TENANT_TABLES:
            logger.error("Unknown tenant table: %s", table_name)
            return False

        async with self.session_factory() as db:
            result = await db.execute(
                text(f"SELECT organization_id FROM {table_name} WHERE id = :id"),
                {"id": entity_id},
            )
            row = result.fetchone()
            if not row:
                return False
            return str(row[0]) == organization_id

    async def get_tenant_stats(self, organization_id: str) -> dict:
        """Get data isolation statistics for a tenant."""
        stats = {}
        async with self.session_factory() as db:
            for table in TENANT_TABLES:
                count = await db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE organization_id = :org_id"),
                    {"org_id": organization_id},
                )
                stats[table] = count.scalar() or 0
        return stats

    @staticmethod
    def validate_org_id(organization_id: str | None) -> str:
        """Validate that org_id is present and valid."""
        if not organization_id:
            raise ValueError("organization_id is required for all profile operations")
        if not isinstance(organization_id, str) or len(organization_id) < 1:
            raise ValueError("organization_id must be a non-empty string")
        return organization_id
