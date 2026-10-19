class IngestionService:
    def enqueue(self, url: str) -> dict[str, str]:
        return {"status": "queued", "url": url}
