"""会话模型"""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Chat")
    name = Column(String, default="")            # 用户自定义名称（可选）
    description = Column(String, default="")      # 会话描述（可选）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    metadata_json = Column("metadata", JSON, default={})

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "name": self.name or "",
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata_json or {}
        }
