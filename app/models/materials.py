"""
素材模型 — 存储上传的文档及其解析后的文本
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), comment="素材标题，默认取文件名")
    file_name: Mapped[str] = mapped_column(String(200), comment="原始文件名")
    file_type: Mapped[str] = mapped_column(String(10), comment="文件类型: pdf/md/txt/docx")
    content: Mapped[str] = mapped_column(Text, comment="解析后的纯文本内容")
    word_count: Mapped[int] = mapped_column(Integer, default=0, comment="字数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Material {self.title}>"
