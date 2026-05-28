"""评论模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    publish_id: Mapped[str] = mapped_column(String(36), ForeignKey("publishes.id"), comment="关联发布记录")
    author: Mapped[str] = mapped_column(String(100), default="", comment="评论者昵称")
    content: Mapped[str] = mapped_column(Text, comment="评论内容")
    # AI 生成的回复建议
    suggested_reply: Mapped[str] = mapped_column(Text, default="", comment="AI建议的回复")
    reply_status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending / replied / ignored")
    replied_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
