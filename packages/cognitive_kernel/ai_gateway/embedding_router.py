class EmbeddingRouter:
    def select_embedding_model(self, content_type: str) -> str:
        if content_type == "code":
            return "google:text-embedding-004" # Placeholder
        else:
            return "google:text-embedding-004"

EMBEDDING_ROUTER = EmbeddingRouter()
