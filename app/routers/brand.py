"""
账号人设路由 — 配置「我是谁」「受众」「风格」「禁忌」
借鉴 XHSSpec 的 brand 概念，精简为 4 个字段
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pathlib import Path

from app.database import get_db
from app.models.brand import BrandProfile

router = APIRouter(prefix="/brand", tags=["账号人设"])


@router.get("/page", response_class=HTMLResponse)
async def brand_page():
    """人设配置页面"""
    html_path = Path("app/static/brand.html")
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>页面未找到</h1>"


@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db)):
    """
    获取当前启用的账号人设
    永远只返回 is_active=True 的那一条，保证 AI 读取时不混乱
    """
    result = await db.execute(
        select(BrandProfile).where(BrandProfile.is_active == True)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return {
            "id": "",
            "identity": "",
            "audience": "",
            "tone": "",
            "taboo": "",
            "is_active": False,
            "message": "还没有配置人设，快去设置吧",
        }

    return {
        "id": profile.id,
        "identity": profile.identity,
        "audience": profile.audience,
        "tone": profile.tone,
        "taboo": profile.taboo,
        "style_matrix": profile.style_matrix or "",
        "is_active": profile.is_active,
    }


@router.post("/profile")
async def save_profile(data: dict, db: AsyncSession = Depends(get_db)):
    """
    保存账号人设 — 新建设置或更新已有设置
    自动把旧的 is_active 关掉，确保只有一条生效
    """
    # 先把所有 profile 的 is_active 关掉
    await db.execute(
        update(BrandProfile).values(is_active=False)
    )

    # 如果传了 id 则是更新，否则新建
    identity = data.get("identity", "")
    audience = data.get("audience", "")
    tone = data.get("tone", "")
    taboo = data.get("taboo", "")
    style_matrix = data.get("style_matrix", "")
    profile_id = data.get("id", "")

    if profile_id:
        result = await db.execute(
            select(BrandProfile).where(BrandProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.identity = identity
            profile.audience = audience
            profile.tone = tone
            profile.taboo = taboo
            profile.style_matrix = style_matrix
            profile.is_active = True
        else:
            raise HTTPException(status_code=404, detail="人设不存在")
    else:
        profile = BrandProfile(
            identity=identity,
            audience=audience,
            tone=tone,
            taboo=taboo,
            style_matrix=style_matrix,
            is_active=True,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return {
        "id": profile.id,
        "identity": profile.identity,
        "audience": profile.audience,
        "tone": profile.tone,
        "taboo": profile.taboo,
        "is_active": profile.is_active,
        "message": "人设保存成功！",
    }
