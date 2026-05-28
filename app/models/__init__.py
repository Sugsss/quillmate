"""数据模型 — 统一管理所有数据库表结构"""
from app.models.materials import Material
from app.models.brand import BrandProfile
from app.models.topics import Topic
from app.models.contents import Content
from app.models.publishes import Publish
from app.models.comments import Comment

__all__ = ["Material", "BrandProfile", "Topic", "Content", "Publish", "Comment"]
