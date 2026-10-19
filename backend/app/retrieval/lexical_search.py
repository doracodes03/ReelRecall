class LexicalSearch:
    def search(self, query: str, items: list[str]) -> list[str]:
        query = query.lower()
        return [item for item in items if query in item.lower()]
