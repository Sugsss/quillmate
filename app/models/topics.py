"""
选题模型 — AI推荐的或手动创建的选题
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(300), comment="选题标题")
    reason: Mapped[str] = mapped_column(Text, default="", comment="选题理由/为什么值得写")
    source: Mapped[str] = mapped_column(String(20), default="manual", comment="来源: ai_suggest / manual")
    audience: Mapped[str] = mapped_column(String(200), default="", comment="目标受众")
    tone: Mapped[str] = mapped_column(String(200), default="", comment="建议风格")
    # 关联素材 — 选题基于哪些素材产生的
    material_ids: Mapped[str] = mapped_column(Text, default="", comment="关联素材ID列表，逗号分隔")
    # 选题增强字段（借鉴huashu-topic-gen）
    topic_type: Mapped[str] = mapped_column(String(20), default="", comment="干货教程型/洞察观点型/案例拆解型/清单合集型")
    workload: Mapped[str] = mapped_column(String(10), default="", comment="工作量评估 ⭐~⭐⭐⭐")
    advantage: Mapped[str] = mapped_column(Text, default="", comment="选题优势")
    risk: Mapped[str] = mapped_column(Text, default="", comment="潜在风险")
    why_today: Mapped[str] = mapped_column(Text, default="", comment="今天为什么值得写")
    status: Mapped[str] = mapped_column(String(20), default="draft", comment="draft / selected / generated / archived")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
