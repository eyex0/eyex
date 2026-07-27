"""πX Memory Engine."""
try:
    from .main import PersistentMemory
except Exception:
    PersistentMemory = None

try:
    from .chunker import TextChunker
except Exception:
    TextChunker = None

try:
    from .normalizer import TextNormalizer
except Exception:
    TextNormalizer = None

try:
    from .vector_memory import VectorMemory, get_vector_memory
except Exception:
    VectorMemory = None
    def get_vector_memory():
        return None

try:
    from .embedding_service import EmbeddingService
except Exception:
    EmbeddingService = None

try:
    from .ingestion_pipeline import IngestionPipeline
except Exception:
    IngestionPipeline = None

__all__ = [
    "PersistentMemory", "TextChunker", "TextNormalizer",
    "VectorMemory", "get_vector_memory", "EmbeddingService", "IngestionPipeline",
]
