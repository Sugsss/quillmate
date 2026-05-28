"""
账号人设模型 — 定义「你是谁」「对谁说话」「什么风格」「不能说什么」
借鉴 XHSSpec 的思路，但精简为 4 个核心字段
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 我是谁 — 一句话描述你的账号定位
    identity: Mapped[str] = mapped_column(String(500), default="", comment="账号定位，如：护肤成分党博主")
    # 受众是谁 — 你的目标读者画像
    audience: Mapped[str] = mapped_column(String(500), default="", comment="目标受众，如：25-35岁关注成分的护肤爱好者")
    # 写作风格 — 说话的语气和风格
    tone: Mapped[str] = mapped_column(String(500), default="", comment="写作风格，如：专业但不晦涩，像跟朋友聊天")
    # 禁忌 — 绝对不能出现的词或话题
    taboo: Mapped[str] = mapped_column(Text, default="", comment="禁忌词/话题，一行一个")
    # 是否启用（只能有一个启用的profile）
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否为当前启用的配置")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<BrandProfile {self.identity[:20]}>"
