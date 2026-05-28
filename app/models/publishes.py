"""发布记录模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Publish(Base):
    __tablename__ = "publishes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id: Mapped[str] = mapped_column(String(36), ForeignKey("contents.id"), comment="关联内容")
    platform: Mapped[str] = mapped_column(String(30), default="xiaohongshu")
    publish_url: Mapped[str] = mapped_column(String(500), default="", comment="发布后的链接")
    status: Mapped[str] = mapped_column(String(20), default="draft", comment="draft / published / archived")
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # 后续通过 Skill 回填的数据
    views: Mapped[int] = mapped_column(Integer, default=0, comment="浏览量")
    likes: Mapped[int] = mapped_column(Integer, default=0, comment="点赞数")
    comments_count: Mapped[int] = mapped_column(Integer, default=0, comment="评论数")
    collects: Mapped[int] = mapped_column(Integer, default=0, comment="收藏数")
    data_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, comment="数据最后更新时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
