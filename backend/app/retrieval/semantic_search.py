class SemanticSearch:
    def search(self, query: str, items: list[str]) -> list[str]:
        return [item for item in items if query.lower() in item.lower()][:5]
