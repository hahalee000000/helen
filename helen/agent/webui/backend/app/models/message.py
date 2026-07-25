"""消息模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    role = Column(String, index=True)  # user, assistant, system
    content = Column(Text)
    attachments = Column(Text, nullable=True)  # JSON: ["upload_id1", "upload_id2", ...]
    timestamp = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "attachments": self.attachments,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
