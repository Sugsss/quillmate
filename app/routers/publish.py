"""
发布路由 — 文案导出、发布记录管理
半自动策略：AI准备好一切，人做最后确认和发布
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.contents import Content
from app.models.publishes import Publish

router = APIRouter(prefix="/publishes", tags=["发布管理"])


@router.post("/create")
async def create_publish(data: dict, db: AsyncSession = Depends(get_db)):
    """
    创建发布记录
    {"content_id": "xxx", "publish_url": "https://...", "published_at": "2024-01-01T12:00:00"}
    """
    content_id = data.get("content_id", "")
    publish_url = data.get("publish_url", "")
    published_at_str = data.get("published_at", "")

    # 验证内容存在
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    published_at = None
    if published_at_str:
        try:
            published_at = datetime.fromisoformat(published_at_str)
        except ValueError:
            published_at = datetime.now()

    pub = Publish(
        content_id=content_id,
        platform=content.platform,
        publish_url=publish_url,
        status="published",
        published_at=published_at or datetime.now(),
    )
    db.add(pub)
    await db.commit()
    await db.refresh(pub)

    return {
        "id": pub.id,
        "content_id": pub.content_id,
        "platform": pub.platform,
        "status": pub.status,
        "publish_url": pub.publish_url,
        "published_at": pub.published_at.isoformat() if pub.published_at else None,
    }


@router.get("/list")
async def list_publishes(db: AsyncSession = Depends(get_db)):
    """发布列表 — 带内容标题"""
    result = await db.execute(
        select(Publish).order_by(Publish.created_at.desc())
    )
    pubs = result.scalars().all()

    items = []
    for p in pubs:
        # 关联查内容标题
        c_result = await db.execute(select(Content).where(Content.id == p.content_id))
        content = c_result.scalar_one_or_none()
        items.append({
            "id": p.id,
            "content_title": content.title if content else "(已删除)",
            "platform": p.platform,
            "status": p.status,
            "publish_url": p.publish_url,
            "views": p.views,
            "likes": p.likes,
            "comments_count": p.comments_count,
            "collects": p.collects,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        })
    return items


@router.get("/export/{content_id}")
async def export_content(content_id: str, db: AsyncSession = Depends(get_db)):
    """
    导出文案 — 生成适合直接复制到小红书的格式
    借鉴 XHSSpec 的 publish package 思路
    """
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    tags_list = content.tags.split() if content.tags else []

    return {
        "platform": content.platform,
        "title": content.title,
        "body": content.body,
        "tags": tags_list,
        "image_suggestion": content.image_suggestion,
        # 组合好的可直接复制文本
        "copy_text": f"{content.title}\n\n{content.body}\n\n{' '.join('#' + t for t in tags_list)}",
    }


@router.put("/{publish_id}/stats")
async def update_stats(publish_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """
    更新发布数据 — 供 Skill 调用
    {"views": 1200, "likes": 85, "comments_count": 12, "collects": 45}
    """
    result = await db.execute(select(Publish).where(Publish.id == publish_id))
    pub = result.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    pub.views = data.get("views", pub.views)
    pub.likes = data.get("likes", pub.likes)
    pub.comments_count = data.get("comments_count", pub.comments_count)
    pub.collects = data.get("collects", pub.collects)
    pub.data_updated_at = datetime.now()

    await db.commit()

    return {
        "id": pub.id,
        "views": pub.views,
        "likes": pub.likes,
        "comments_count": pub.comments_count,
        "collects": pub.collects,
        "data_updated_at": pub.data_updated_at.isoformat(),
    }
