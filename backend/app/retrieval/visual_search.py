class VisualSearch:
    def search(self, query: str, items: list[str]) -> list[str]:
        return [item for item in items if "visual" in query.lower() or "scene" in query.lower()]
