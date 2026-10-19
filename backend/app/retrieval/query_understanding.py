class QueryUnderstanding:
    def normalize(self, query: str) -> str:
        return query.strip().lower()
