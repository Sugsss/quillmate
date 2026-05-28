"""
数据分析路由 — 发布效果看板
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.publishes import Publish
from app.models.contents import Content

router = APIRouter(prefix="/analytics", tags=["数据分析"])


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """数据看板 — 汇总统计"""
    # 总发布数
    total_result = await db.execute(select(func.count(Publish.id)))
    total = total_result.scalar() or 0

    # 总互动
    stats_result = await db.execute(
        select(
            func.sum(Publish.views),
            func.sum(Publish.likes),
            func.sum(Publish.comments_count),
            func.sum(Publish.collects),
        )
    )
    total_views, total_likes, total_comments, total_collects = stats_result.one()
    total_views = total_views or 0
    total_likes = total_likes or 0
    total_comments = total_comments or 0
    total_collects = total_collects or 0

    return {
        "total_publishes": total,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_collects": total_collects,
        "engagement_rate": f"{(total_likes + total_collects + total_comments) / max(total_views, 1) * 100:.1f}%",
    }


@router.get("/posts")
async def posts_ranking(db: AsyncSession = Depends(get_db)):
    """内容排行 — 按互动排序"""
    result = await db.execute(
        select(Publish).order_by(Publish.views.desc()).limit(20)
    )
    pubs = result.scalars().all()

    items = []
    for p in pubs:
        c_result = await db.execute(select(Content).where(Content.id == p.content_id))
        content = c_result.scalar_one_or_none()
        items.append({
            "id": p.id,
            "title": content.title if content else "(已删除)",
            "platform": p.platform,
            "views": p.views,
            "likes": p.likes,
            "comments_count": p.comments_count,
            "collects": p.collects,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "data_updated_at": p.data_updated_at.isoformat() if p.data_updated_at else None,
        })

    return items
