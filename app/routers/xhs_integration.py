"""
小红书集成路由 — 数据采集 + 趋势分析 + 一键发布
基于 Spider_XHS 的 HTTP API 能力
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.models.contents import Content
from app.models.publishes import Publish
from app.models.comments import Comment
from app.services.xhs_client import xhs_client, XHS_ENABLED

router = APIRouter(prefix="/xhs", tags=["小红书集成"])


# ═══════════════════════════════════════════
# 状态检查
# ═══════════════════════════════════════════

@router.get("/status")
async def xhs_status():
    """检查小红书API配置状态"""
    if not XHS_ENABLED:
        return {
            "enabled": False,
            "message": "未配置 XHS_COOKIE 环境变量。请在小红书网页端登录后，从浏览器开发者工具中复制 Cookie 设置到 .env 文件中。",
            "setup_guide": "1. 浏览器打开 xiaohongshu.com 并登录\n2. F12 → Application → Cookies → 复制完整Cookie字符串\n3. 在项目 .env 中添加: XHS_COOKIE=你的cookie",
        }

    login = await xhs_client.check_login()
    return {
        "enabled": True,
        "login_status": login,
    }


# ═══════════════════════════════════════════
# 数据采集 & 趋势分析
# ═══════════════════════════════════════════

@router.get("/search")
async def search_notes(keyword: str, count: int = 20, sort: str = "general"):
    """
    搜索小红书笔记
    sort: general(综合) / popularity_descending(最热) / time_descending(最新)
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")
    return await xhs_client.search_notes(keyword, page_size=count, sort=sort)


@router.get("/trending")
async def trending_notes(keyword: str, count: int = 20):
    """
    获取热门笔记 + 趋势分析
    返回热门笔记列表、高频标签、标题模式
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")
    return await xhs_client.get_trending_notes(keyword, count=count)


@router.get("/trend-insights")
async def trend_insights(keyword: str):
    """
    深度趋势洞察：标题公式分析 + 内容规律
    可作为AI选题推荐的辅助数据
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")
    return await xhs_client.extract_trend_insights(keyword)


@router.get("/note/{note_id}")
async def note_detail(note_id: str):
    """获取单条笔记详情（含互动数据）"""
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")
    return await xhs_client.get_note_detail(note_id)


# ═══════════════════════════════════════════
# 一键发布
# ═══════════════════════════════════════════

@router.post("/publish")
async def publish_to_xhs(data: dict, db: AsyncSession = Depends(get_db)):
    """
    一键发布到小红书

    请求体:
    {
        "content_id": "已生成内容的ID",
        "is_public": true
    }
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE，无法发布")

    content_id = data.get("content_id", "")
    is_public = data.get("is_public", True)

    # 获取内容
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    tags_list = content.tags.split() if content.tags else []

    # 调用小红书API发布
    publish_result = await xhs_client.publish_note(
        title=content.title,
        content=content.body,
        tags=tags_list,
        is_public=is_public,
    )

    # 记录发布
    if publish_result.get("published"):
        pub = Publish(
            content_id=content_id,
            platform="xiaohongshu",
            publish_url=publish_result.get("url", ""),
            status="published",
            published_at=datetime.now(),
        )
        db.add(pub)
        await db.commit()
        await db.refresh(pub)
        publish_result["publish_id"] = pub.id

    return publish_result


# ═══════════════════════════════════════════
# 自动数据追踪
# ═══════════════════════════════════════════

@router.post("/sync-stats/{publish_id}")
async def sync_publish_stats(publish_id: str, db: AsyncSession = Depends(get_db)):
    """
    自动同步发布数据 — 从XHS获取最新互动数据
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")

    result = await db.execute(select(Publish).where(Publish.id == publish_id))
    pub = result.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    # 从发布链接中提取note_id
    note_id = ""
    if pub.publish_url:
        parts = pub.publish_url.rstrip("/").split("/")
        note_id = parts[-1] if parts else ""

    if not note_id:
        raise HTTPException(status_code=400, detail="无法从发布链接提取笔记ID")

    detail = await xhs_client.get_note_detail(note_id)
    if detail.get("error"):
        raise HTTPException(status_code=500, detail=detail["error"])

    # 更新数据
    pub.views = detail.get("views", pub.views)
    pub.likes = detail.get("likes", pub.likes)
    pub.comments_count = detail.get("comments", pub.comments_count)
    pub.collects = detail.get("collects", pub.collects)
    pub.data_updated_at = datetime.now()
    await db.commit()

    return {
        "publish_id": publish_id,
        "views": pub.views,
        "likes": pub.likes,
        "comments_count": pub.comments_count,
        "collects": pub.collects,
        "updated_at": pub.data_updated_at.isoformat(),
    }


@router.post("/sync-comments/{publish_id}")
async def sync_comments(publish_id: str, db: AsyncSession = Depends(get_db)):
    """
    自动同步评论数据 — 从XHS拉取最新评论
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")

    result = await db.execute(select(Publish).where(Publish.id == publish_id))
    pub = result.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    note_id = ""
    if pub.publish_url:
        parts = pub.publish_url.rstrip("/").split("/")
        note_id = parts[-1] if parts else ""

    if not note_id:
        raise HTTPException(status_code=400, detail="无法从发布链接提取笔记ID")

    comments_data = await xhs_client.get_note_comments(note_id)
    if comments_data.get("error"):
        raise HTTPException(status_code=500, detail=comments_data["error"])

    new_count = 0
    for c in comments_data.get("comments", []):
        # 检查是否已存在
        existing = await db.execute(
            select(Comment).where(Comment.publish_id == publish_id)
        )
        existing_ids = {c2.content[:50] for c2 in existing.scalars().all()}

        if c["content"][:50] not in existing_ids:
            comment = Comment(
                publish_id=publish_id,
                author=c.get("author", ""),
                content=c.get("content", ""),
                reply_status="pending",
            )
            db.add(comment)
            new_count += 1

    await db.commit()
    return {"synced": new_count, "total": len(comments_data.get("comments", []))}


@router.post("/sync-all")
async def sync_all_publishes(db: AsyncSession = Depends(get_db)):
    """
    一键同步所有已发布内容的数据
    """
    if not XHS_ENABLED:
        raise HTTPException(status_code=400, detail="未配置XHS_COOKIE")

    result = await db.execute(
        select(Publish).where(Publish.status == "published").order_by(Publish.published_at.desc()).limit(10)
    )
    pubs = result.scalars().all()

    synced = 0
    errors = 0
    for pub in pubs:
        try:
            note_id = ""
            if pub.publish_url:
                parts = pub.publish_url.rstrip("/").split("/")
                note_id = parts[-1] if parts else ""

            if note_id:
                detail = await xhs_client.get_note_detail(note_id)
                if not detail.get("error"):
                    pub.views = detail.get("views", pub.views)
                    pub.likes = detail.get("likes", pub.likes)
                    pub.comments_count = detail.get("comments", pub.comments_count)
                    pub.collects = detail.get("collects", pub.collects)
                    pub.data_updated_at = datetime.now()
                    synced += 1
                else:
                    errors += 1
        except Exception:
            errors += 1

    await db.commit()
    return {"synced": synced, "errors": errors, "total": len(pubs)}
