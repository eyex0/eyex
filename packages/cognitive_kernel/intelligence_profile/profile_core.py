"""
πX Profile Core — IntelligenceProfile dataclass, ProfileManager, ProfileVersionManager.

The ProfileManager handles CRUD operations against the intelligence_profiles table.
The ProfileVersionManager tracks full version history with JSONB snapshots and diffs.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.core")


@dataclass
class IntelligenceProfile:
    """The adaptive intelligence identity for an organization."""
    id: str
    organization_id: str
    industry: str | None = None
    business_model: str | None = None
    company_size: str | None = None
    region: str | None = None
    locations: list[dict] = field(default_factory=list)
    # profile_config holds the full adaptive configuration:
    # departments, roles, workflows, processes, agents, policies, models, dashboards
    profile_config: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    status: str = "draft"  # draft | active | archived
    current_version: int = 1
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "industry": self.industry,
            "business_model": self.business_model,
            "company_size": self.company_size,
            "region": self.region,
            "locations": self.locations,
            "profile_config": self.profile_config,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "current_version": self.current_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: Any) -> IntelligenceProfile:
        return cls(
            id=str(row[0]),
            organization_id=str(row[1]),
            industry=row[2],
            business_model=row[3],
            company_size=row[4],
            region=row[5],
            locations=row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]"),
            profile_config=row[7] if isinstance(row[7], dict) else json.loads(row[7] or "{}"),
            confidence_score=float(row[8] or 0.0),
            status=row[9],
            current_version=int(row[10] or 1),
            created_at=str(row[11]) if row[11] else None,
            updated_at=str(row[12]) if row[12] else None,
        )


class ProfileManager:
    """CRUD operations for intelligence profiles with tenant isolation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create(
        self,
        organization_id: str,
        industry: str | None = None,
        business_model: str | None = None,
        company_size: str | None = None,
        region: str | None = None,
        locations: list | None = None,
        profile_config: dict | None = None,
    ) -> IntelligenceProfile:
        profile_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO intelligence_profiles "
                    "(id, organization_id, industry, business_model, company_size, region, "
                    "locations, profile_config, status, current_version) "
                    "VALUES (:id, :org_id, :industry, :biz_model, :size, :region, "
                    ":locations, :config, 'draft', 1)"
                ),
                {
                    "id": profile_id,
                    "org_id": organization_id,
                    "industry": industry,
                    "biz_model": business_model,
                    "size": company_size,
                    "region": region,
                    "locations": json.dumps(locations or []),
                    "config": json.dumps(profile_config or {}),
                },
            )
            await db.commit()
        logger.info("Created intelligence profile %s for org %s", profile_id, organization_id)
        profile = await self.get(organization_id, profile_id)
        assert profile is not None
        return profile

    async def get(self, organization_id: str, profile_id: str) -> IntelligenceProfile | None:
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT * FROM intelligence_profiles "
                    "WHERE id = :id AND organization_id = :org_id"
                ),
                {"id": profile_id, "org_id": organization_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return IntelligenceProfile.from_row(row)

    async def get_by_org(self, organization_id: str) -> IntelligenceProfile | None:
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT * FROM intelligence_profiles "
                    "WHERE organization_id = :org_id AND status != 'archived' "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"org_id": organization_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return IntelligenceProfile.from_row(row)

    async def update(
        self,
        organization_id: str,
        profile_id: str,
        updates: dict[str, Any],
        changed_by: str | None = None,
        change_reason: str | None = None,
    ) -> IntelligenceProfile | None:
        # Build SET clause dynamically from updates
        allowed_fields = {
            "industry", "business_model", "company_size", "region",
            "locations", "profile_config", "confidence_score", "status",
        }
        set_clauses = []
        params: dict[str, Any] = {"id": profile_id, "org_id": organization_id}
        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(value) if isinstance(value, (dict, list)) else value

        if not set_clauses:
            return await self.get(organization_id, profile_id)

        # Increment version
        set_clauses.append("current_version = current_version + 1")
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        async with self.session_factory() as db:
            # Get current state for version snapshot
            current = await db.execute(
                text("SELECT * FROM intelligence_profiles WHERE id = :id AND organization_id = :org_id"),
                {"id": profile_id, "org_id": organization_id},
            )
            current_row = current.fetchone()
            if not current_row:
                return None

            old_version = int(current_row[10] or 1)

            # Apply update
            await db.execute(
                text(f"UPDATE intelligence_profiles SET {', '.join(set_clauses)} WHERE id = :id AND organization_id = :org_id"),
                params,
            )

            # Create version snapshot
            await self._create_version(db, profile_id, organization_id, old_version + 1, current_row, updates, changed_by, change_reason)

            await db.commit()

        return await self.get(organization_id, profile_id)

    async def activate(self, organization_id: str, profile_id: str) -> IntelligenceProfile | None:
        return await self.update(
            organization_id, profile_id, {"status": "active"},
            changed_by=None, change_reason="Profile activated",
        )

    async def archive(self, organization_id: str, profile_id: str) -> IntelligenceProfile | None:
        return await self.update(
            organization_id, profile_id, {"status": "archived"},
            changed_by=None, change_reason="Profile archived",
        )

    async def list_versions(self, organization_id: str, profile_id: str, limit: int = 50) -> list[dict]:
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT id, version_number, diff, changed_by, change_reason, created_at "
                    "FROM profile_versions WHERE profile_id = :pid AND organization_id = :org_id "
                    "ORDER BY version_number DESC LIMIT :limit"
                ),
                {"pid": profile_id, "org_id": organization_id, "limit": limit},
            )
            return [
                {
                    "id": str(r[0]),
                    "version_number": r[1],
                    "diff": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
                    "changed_by": str(r[3]) if r[3] else None,
                    "change_reason": r[4],
                    "created_at": str(r[5]),
                }
                for r in result.fetchall()
            ]

    async def get_version(self, organization_id: str, profile_id: str, version_number: int) -> dict | None:
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT id, version_number, snapshot, diff, changed_by, change_reason, created_at "
                    "FROM profile_versions WHERE profile_id = :pid AND organization_id = :org_id "
                    "AND version_number = :vn"
                ),
                {"pid": profile_id, "org_id": organization_id, "vn": version_number},
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "id": str(row[0]),
                "version_number": row[1],
                "snapshot": row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}"),
                "diff": row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}"),
                "changed_by": str(row[4]) if row[4] else None,
                "change_reason": row[5],
                "created_at": str(row[6]),
            }

    async def _create_version(
        self, db: AsyncSession, profile_id: str, org_id: str,
        new_version: int, current_row: Any, updates: dict,
        changed_by: str | None, change_reason: str | None,
    ):
        # Build snapshot from current row
        snapshot = {
            "id": str(current_row[0]),
            "organization_id": str(current_row[1]),
            "industry": current_row[2],
            "business_model": current_row[3],
            "company_size": current_row[4],
            "region": current_row[5],
            "locations": current_row[6] if isinstance(current_row[6], list) else json.loads(current_row[6] or "[]"),
            "profile_config": current_row[7] if isinstance(current_row[7], dict) else json.loads(current_row[7] or "{}"),
            "confidence_score": float(current_row[8] or 0.0),
            "status": current_row[9],
            "current_version": new_version,
        }
        # Build diff
        diff = {k: {"old": None, "new": v} for k, v in updates.items()}

        await db.execute(
            text(
                "INSERT INTO profile_versions "
                "(id, profile_id, organization_id, version_number, snapshot, diff, changed_by, change_reason) "
                "VALUES (:id, :pid, :org_id, :vn, :snapshot, :diff, :cb, :cr)"
            ),
            {
                "id": str(uuid.uuid4()),
                "pid": profile_id,
                "org_id": org_id,
                "vn": new_version,
                "snapshot": json.dumps(snapshot),
                "diff": json.dumps(diff),
                "cb": changed_by,
                "cr": change_reason,
            },
        )


class ProfileVersionManager:
    """Manages profile version history, diff tracking, and rollbacks."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self._manager = ProfileManager(session_factory)

    async def get_history(self, organization_id: str, profile_id: str, limit: int = 50) -> list[dict]:
        return await self._manager.list_versions(organization_id, profile_id, limit)

    async def get_version(self, organization_id: str, profile_id: str, version_number: int) -> dict | None:
        return await self._manager.get_version(organization_id, profile_id, version_number)

    async def rollback(
        self, organization_id: str, profile_id: str, target_version: int,
        changed_by: str | None = None,
    ) -> IntelligenceProfile | None:
        """Restore profile to a specific version."""
        version_data = await self.get_version(organization_id, profile_id, target_version)
        if not version_data:
            return None

        snapshot = version_data["snapshot"]
        # Apply snapshot as update
        updates = {
            "industry": snapshot.get("industry"),
            "business_model": snapshot.get("business_model"),
            "company_size": snapshot.get("company_size"),
            "region": snapshot.get("region"),
            "locations": snapshot.get("locations", []),
            "profile_config": snapshot.get("profile_config", {}),
            "confidence_score": snapshot.get("confidence_score", 0.0),
            "status": snapshot.get("status", "draft"),
        }
        return await self._manager.update(
            organization_id, profile_id, updates,
            changed_by=changed_by,
            change_reason=f"Rollback to version {target_version}",
        )
