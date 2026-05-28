"""
评论管理路由 — AI 生成回复建议，预留自动回复
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.comments import Comment
from app.models.publishes import Publish
from app.models.contents import Content
from app.models.brand import BrandProfile
from app.services.llm import call_llm

router = APIRouter(prefix="/comments", tags=["评论管理"])

REPLY_SYSTEM_PROMPT = """你是一个小红书博主的助手，负责为博主生成评论回复建议。

## 回复风格
- 真诚、友好、像跟朋友聊天
- 不要过于官方或营销感
- 如果评论是提问，认真回答
- 如果评论是夸奖，真诚感谢
- 如果评论是批评，虚心接受或礼貌解释
- 回复要简短（50字以内）
- 可以适当用1-2个emoji

## 输出格式
返回 JSON：{"reply": "回复内容"}"""


@router.post("/add")
async def add_comment(data: dict, db: AsyncSession = Depends(get_db)):
    """
    添加评论 — 供 Skill 调用
    {"publish_id": "xxx", "author": "用户A", "content": "这个好用吗？"}
    """
    publish_id = data.get("publish_id", "")
    author = data.get("author", "匿名用户")
    content = data.get("content", "")

    if not content.strip():
        raise HTTPException(status_code=400, detail="评论内容不能为空")

    # 验证发布记录存在
    result = await db.execute(select(Publish).where(Publish.id == publish_id))
    pub = result.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    comment = Comment(
        publish_id=publish_id,
        author=author,
        content=content,
        reply_status="pending",
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return {
        "id": comment.id,
        "author": comment.author,
        "content": comment.content,
        "reply_status": comment.reply_status,
    }


@router.post("/{comment_id}/suggest-reply")
async def suggest_reply(comment_id: str, db: AsyncSession = Depends(get_db)):
    """AI 生成回复建议"""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    # 获取关联内容上下文
    pub_result = await db.execute(select(Publish).where(Publish.id == comment.publish_id))
    pub = pub_result.scalar_one_or_none()

    context = ""
    if pub:
        c_result = await db.execute(select(Content).where(Content.id == pub.content_id))
        content = c_result.scalar_one_or_none()
        if content:
            context = f"你的笔记标题是：{content.title}\n笔记内容是：{content.body[:300]}"

    # 获取品牌人设
    brand_result = await db.execute(select(BrandProfile).where(BrandProfile.is_active == True))
    brand = brand_result.scalar_one_or_none()
    tone = brand.tone if brand else "真诚友好"

    user_prompt = f"{context}\n\n有人评论了你的笔记：\n评论者：{comment.author}\n评论内容：{comment.content}\n\n请以{ tone }的风格生成一条回复。只返回JSON。"

    try:
        raw = await call_llm(REPLY_SYSTEM_PROMPT, user_prompt, temperature=0.7, max_tokens=200)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        reply_data = json.loads(cleaned)
        reply_text = reply_data.get("reply", "")
    except Exception:
        reply_text = f"谢谢{'你的支持！' if '好' in comment.content or '赞' in comment.content else '你的评论！'}😊"

    # 保存建议
    comment.suggested_reply = reply_text
    await db.commit()

    return {
        "comment_id": comment.id,
        "comment_content": comment.content,
        "suggested_reply": reply_text,
    }


@router.get("/list")
async def list_comments(publish_id: str = "", status: str = "", db: AsyncSession = Depends(get_db)):
    """评论列表 — 可按发布记录和状态筛选"""
    query = select(Comment).order_by(Comment.created_at.desc())
    if publish_id:
        query = query.where(Comment.publish_id == publish_id)
    if status:
        query = query.where(Comment.reply_status == status)

    result = await db.execute(query)
    comments = result.scalars().all()

    return [
        {
            "id": c.id,
            "publish_id": c.publish_id,
            "author": c.author,
            "content": c.content,
            "suggested_reply": c.suggested_reply,
            "reply_status": c.reply_status,
            "created_at": c.created_at.isoformat(),
        }
        for c in comments
    ]


@router.put("/{comment_id}/status")
async def update_status(comment_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """更新评论回复状态"""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    new_status = data.get("status", "replied")
    if new_status not in ("pending", "replied", "ignored"):
        raise HTTPException(status_code=400, detail="无效状态")

    comment.reply_status = new_status
    await db.commit()

    return {"id": comment.id, "reply_status": comment.reply_status}
