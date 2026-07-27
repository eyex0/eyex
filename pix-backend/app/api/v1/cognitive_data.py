from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import json
import uuid

from app.cognitive_data_layer import CognitiveDataPipeline
from app.cognitive_data_layer.import_service import ImportService
from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger("pix.api.cognitive_data")

cognitive_data_router = APIRouter(prefix="/cognitive-data", tags=["Cognitive Data Layer"])


@cognitive_data_router.post("/process")
async def process_upload(
    file: UploadFile = File(...),
    company_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    pipeline = CognitiveDataPipeline()
    result = await pipeline.process(
        content,
        company_id=company_id or str(user.organization_id),
        hint=file.filename.split(".")[-1] if file.filename else None,
    )
    canonical = result["canonical"]
    return {
        "source_name": canonical.source_name,
        "source_format": canonical.source_format,
        "sheets": [
            {
                "name": sheet.name,
                "tables": [
                    {
                        "name": table.name,
                        "columns": [
                            {
                                "name": c.name,
                                "entity_type": c.entity_type.value if c.entity_type else None,
                                "semantic_type": c.semantic_type.value,
                                "confidence": c.confidence,
                            }
                            for c in table.columns
                        ],
                        "row_count": len(table.rows),
                        "primary_keys": table.primary_keys,
                    }
                    for table in sheet.tables
                ],
            }
            for sheet in canonical.sheets
        ],
        "entities": {k.value: v for k, v in canonical.entities.items()},
        "quality": result["quality_report"],
        "confidence": result["confidence_report"],
        "knowledge_graph": result["knowledge_graph"],
    }


@cognitive_data_router.get("/supported-formats")
async def supported_formats() -> dict[str, Any]:
    from app.cognitive_data_layer.parser import get_parser_registry

    return {"formats": get_parser_registry().list_parsers()}


@cognitive_data_router.post("/import")
async def import_data(
    dataset_id: uuid.UUID = Query(...),
    mappings: str = Query(..., description="JSON string of column mappings"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        mappings_dict = json.loads(mappings)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid mappings JSON")

    hint = file.filename.split(".")[-1] if file.filename else None

    report = await ImportService.import_dataset(
        session=db,
        dataset_id=dataset_id,
        file_content=content,
        file_hint=hint,
        mappings=mappings_dict,
    )
    return report
