"""
选题路由 — AI 推荐选题 + 手动创建
融合：素材驱动（主线）+ 趋势分析（辅线）
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.materials import Material
from app.models.brand import BrandProfile
from app.models.topics import Topic
from app.services.llm import call_llm
from app.prompts.topic_suggest import TOPIC_SUGGEST_SYSTEM, build_topic_suggest_prompt

router = APIRouter(prefix="/topics", tags=["选题管理"])


@router.post("/suggest")
async def suggest_topics(db: AsyncSession = Depends(get_db)):
    """
    AI 推荐选题 — 读取素材库 + 人设 → 推荐 5 个选题

    主线逻辑：基于素材内容推荐有深度的选题
    后续可扩展辅线：分析热门趋势辅助
    """
    # 1. 获取所有素材摘要
    result = await db.execute(select(Material).order_by(Material.created_at.desc()))
    materials = result.scalars().all()

    if not materials:
        raise HTTPException(status_code=400, detail="素材库为空，请先上传素材")

    # 构建素材摘要（避免超长，每篇取前500字）
    summaries = []
    for m in materials:
        summaries.append(f"【{m.title}】({m.word_count}字)\n{m.content[:500]}")
    materials_summary = "\n\n---\n\n".join(summaries)

    # 2. 获取账号人设
    brand_result = await db.execute(
        select(BrandProfile).where(BrandProfile.is_active == True)
    )
    brand = brand_result.scalar_one_or_none()
    identity = brand.identity if brand else ""
    audience = brand.audience if brand else ""
    tone = brand.tone if brand else ""

    # 3. 调用 LLM 生成选题
    user_prompt = build_topic_suggest_prompt(materials_summary, identity, audience, tone)

    try:
        response = await call_llm(TOPIC_SUGGEST_SYSTEM, user_prompt, temperature=0.8)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {str(e)}")

    # 4. 解析 JSON
    try:
        # 清理可能的 markdown 代码块标记
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        data = json.loads(cleaned)
        topics = data.get("topics", [])
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"AI 返回格式异常: {response[:200]}")

    # 5. 入库
    saved = []
    material_ids = ",".join(m.id for m in materials)
    for t in topics:
        topic = Topic(
            title=t.get("title", ""),
            reason=t.get("reason", ""),
            source="ai_suggest",
            audience=t.get("audience", audience),
            tone=t.get("tone", tone),
            material_ids=material_ids,
            topic_type=t.get("type", ""),
            workload=t.get("workload", ""),
            advantage=t.get("advantage", ""),
            risk=t.get("risk", ""),
            status="draft",
        )
        db.add(topic)
        saved.append(topic)

    await db.commit()

    return {
        "count": len(saved),
        "topics": [
            {
                "id": t.id,
                "title": t.title,
                "reason": t.reason,
                "type": t.topic_type,
                "workload": t.workload,
                "advantage": t.advantage,
                "risk": t.risk,
                "audience": t.audience,
                "tone": t.tone,
            }
            for t in saved
        ],
    }


@router.post("/create")
async def create_topic(data: dict, db: AsyncSession = Depends(get_db)):
    """手动创建选题"""
    topic = Topic(
        title=data.get("title", ""),
        reason=data.get("reason", ""),
        source="manual",
        audience=data.get("audience", ""),
        tone=data.get("tone", ""),
        material_ids=data.get("material_ids", ""),
        status="draft",
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return {"id": topic.id, "title": topic.title, "status": topic.status}


@router.get("/list")
async def list_topics(status: str = "", db: AsyncSession = Depends(get_db)):
    """选题列表"""
    query = select(Topic).order_by(Topic.created_at.desc())
    if status:
        query = query.where(Topic.status == status)
    result = await db.execute(query)
    topics = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "reason": t.reason,
            "type": t.topic_type,
            "workload": t.workload,
            "advantage": t.advantage,
            "risk": t.risk,
            "source": t.source,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in topics
    ]


@router.delete("/{topic_id}")
async def delete_topic(topic_id: str, db: AsyncSession = Depends(get_db)):
    """删除选题"""
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")
    await db.delete(topic)
    await db.commit()
    return {"ok": True}
