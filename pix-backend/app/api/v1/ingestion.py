import logging
from fastapi import APIRouter, Depends, File, UploadFile
from packages.cognitive-kernel.ingestion import run_ingestion_pipeline

logger = logging.getLogger("pix.api.ingestion")

ingestion_router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

@ingestion_router.post("/excel/analyze")
async def analyze_excel(file: UploadFile = File(...)):
    content = await file.read()
    results = run_ingestion_pipeline(file.filename, content)
    return results
