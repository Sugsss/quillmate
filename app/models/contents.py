"""生成内容模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id"), comment="关联选题")
    platform: Mapped[str] = mapped_column(String(30), default="xiaohongshu", comment="目标平台")
    title: Mapped[str] = mapped_column(String(500), comment="生成的标题")
    body: Mapped[str] = mapped_column(Text, comment="正文内容")
    tags: Mapped[str] = mapped_column(String(500), comment="话题标签，空格分隔")
    image_suggestion: Mapped[str] = mapped_column(Text, default="", comment="配图建议")
    version: Mapped[int] = mapped_column(default=1, comment="第几版")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
