from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.core.database import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=True)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    result_count = Column(String, default="0")
