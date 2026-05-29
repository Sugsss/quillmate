"""
内容生成路由 — 双专家引擎生成小红书文案
分析专家读素材提取角度 → 创作专家写人味文案
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.topics import Topic
from app.models.materials import Material
from app.models.brand import BrandProfile
from app.models.contents import Content
from app.services.llm import call_llm
from app.services.safety import filter_sensitive, clean_content
from app.services.proofreader import proofread_content
from app.prompts.content_generate import (
    ANALYSIS_SYSTEM,
    build_analysis_prompt,
    build_generate_prompt,
)

router = APIRouter(prefix="/contents", tags=["内容生成"])


@router.get("/list")
async def list_contents(db: AsyncSession = Depends(get_db)):
    """已生成内容列表 — 返回所有内容摘要"""
    result = await db.execute(
        select(Content).order_by(Content.created_at.desc())
    )
    contents = result.scalars().all()
    return [
        {
            "id": c.id,
            "topic_id": c.topic_id,
            "platform": c.platform,
            "title": c.title,
            "body_preview": c.body[:150],
            "tags": c.tags.split() if c.tags else [],
            "version": c.version,
            "created_at": c.created_at.isoformat(),
        }
        for c in contents
    ]


@router.get("/{content_id}")
async def get_content(content_id: str, db: AsyncSession = Depends(get_db)):
    """查看单条内容的完整信息"""
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    # 查关联选题
    topic_result = await db.execute(select(Topic).where(Topic.id == content.topic_id))
    topic = topic_result.scalar_one_or_none()

    return {
        "id": content.id,
        "topic_id": content.topic_id,
        "topic_title": topic.title if topic else "",
        "platform": content.platform,
        "title": content.title,
        "body": content.body,
        "tags": content.tags.split() if content.tags else [],
        "image_suggestion": content.image_suggestion,
        "version": content.version,
        "created_at": content.created_at.isoformat(),
    }


@router.post("/generate")
async def generate_content(data: dict, db: AsyncSession = Depends(get_db)):
    """
    生成小红书文案 — 双专家引擎

    请求体:
    {
        "topic_id": "选题ID",
        "material_ids": ["素材ID1", "素材ID2"],  // 可选，不传则使用选题关联的素材
        "platform": "xiaohongshu"
    }
    """
    topic_id = data.get("topic_id", "")
    material_ids = data.get("material_ids", [])
    platform = data.get("platform", "xiaohongshu")
    custom_analysis_prompt = data.get("analysis_prompt", "")
    custom_creation_prompt = data.get("creation_prompt", "")

    # 1. 获取选题
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="选题不存在")

    # 2. 获取关联素材
    if not material_ids and topic.material_ids:
        material_ids = [mid.strip() for mid in topic.material_ids.split(",") if mid.strip()]

    materials_content = ""
    if material_ids:
        for mid in material_ids[:3]:  # 最多取3篇素材
            m_result = await db.execute(select(Material).where(Material.id == mid))
            m = m_result.scalar_one_or_none()
            if m:
                materials_content += f"\n\n---\n【{m.title}】\n{m.content[:2000]}"
    else:
        # 如果没指定素材，取全部素材摘要
        all_result = await db.execute(select(Material).limit(5))
        for m in all_result.scalars().all():
            materials_content += f"\n\n---\n【{m.title}】\n{m.content[:800]}"

    if not materials_content.strip():
        raise HTTPException(status_code=400, detail="没有可用的素材内容")

    # 3. 获取品牌人设
    brand_result = await db.execute(
        select(BrandProfile).where(BrandProfile.is_active == True)
    )
    brand = brand_result.scalar_one_or_none()
    identity = brand.identity if brand else ""
    audience = brand.audience if brand else topic.audience
    tone = brand.tone if brand else topic.tone
    taboo = brand.taboo if brand else ""
    style_matrix = brand.style_matrix if brand else ""

    # 匹配视觉风格
    matched_style = {}
    if style_matrix and topic.topic_type:
        try:
            sm = json.loads(style_matrix)
            matched_style = sm.get(topic.topic_type, {})
        except Exception:
            pass

    # ── 第一阶段：分析专家 ──
    analysis_system = ANALYSIS_SYSTEM
    if custom_analysis_prompt.strip():
        analysis_system = custom_analysis_prompt.strip() + "\n\n返回 JSON：{\"angle\":\"角度\",\"key_points\":[\"要点\"],\"structure\":\"结构\",\"emotion\":\"基调\"}"
    analysis_input = build_analysis_prompt(materials_content, topic.title, topic.reason)
    try:
        analysis_raw = await call_llm(analysis_system, analysis_input, temperature=0.5)
        # 解析分析结果
        cleaned = analysis_raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        analysis_data = json.loads(cleaned)
    except Exception:
        # 分析失败不阻断，用降级方案
        analysis_data = {
            "angle": topic.reason,
            "key_points": [topic.title],
            "structure": "痛点→方案→体验→互动",
            "emotion": "真实分享",
        }

    # ── 第二阶段：创作专家 ──
    sys_prompt, user_prompt = build_generate_prompt(
        analysis_result=json.dumps(analysis_data, ensure_ascii=False),
        topic_title=topic.title,
        identity=identity,
        audience=audience,
        tone=tone,
        taboo=taboo,
    )
    # 注入品牌视觉风格
    if matched_style:
        style_hint = f"\n\n## 品牌视觉风格（优先使用）\n风格：{matched_style.get('style','')}\n底色：{matched_style.get('bg','')}\n主色：{matched_style.get('main','')}"
        sys_prompt += style_hint
    if custom_creation_prompt.strip():
        sys_prompt = custom_creation_prompt.strip() + "\n\n## 输出格式\n严格返回 JSON，不要 markdown 代码块：\n{\"title\":\"标题\",\"body\":\"正文\",\"tags\":[\"标签\"],\"image_suggestion\":\"AI生图提示词，Midjourney/Stable Diffusion格式\"",\"image_design\":{\"style\":\"自由发挥\",\"bg_color\":\"#色\",\"main_color\":\"#色\",\"layout\":\"排版\",\"typography\":\"字体\"}}"

    try:
        content_raw = await call_llm(sys_prompt, user_prompt, temperature=0.85, max_tokens=3000)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")

    # 解析生成结果（增强容错）
    try:
        cleaned = content_raw.strip()
        # 尝试从 markdown 代码块中提取 JSON
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1].strip()
        # 尝试找到第一个 { 到最后一个 }
        if not cleaned.startswith("{"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                cleaned = cleaned[start:end+1]
        content_data = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        raise HTTPException(status_code=500, detail=f"AI 返回格式异常: {content_raw[:300]}")

    # ── 敏感词检测 ──
    full_text = content_data.get("title", "") + content_data.get("body", "")
    safety_check = filter_sensitive(full_text)

    # 自动清洗
    title = clean_content(content_data.get("title", ""))
    body = clean_content(content_data.get("body", ""))
    tags = content_data.get("tags", [])
    image_suggestion = content_data.get("image_suggestion", "")
    image_design = content_data.get("image_design", {})  # 新增：配图设计方案

    # 入库
    content_record = Content(
        topic_id=topic_id,
        platform=platform,
        title=title,
        body=body,
        tags=" ".join(tags) if isinstance(tags, list) else tags,
        image_suggestion=image_suggestion,
    )
    db.add(content_record)

    # 更新选题状态
    topic.status = "generated"

    await db.commit()
    await db.refresh(content_record)

    return {
        "id": content_record.id,
        "topic_id": topic_id,
        "platform": platform,
        "title": title,
        "body": body,
        "tags": tags,
        "image_suggestion": image_suggestion,
        "image_design": image_design,
        "safety": safety_check,
        "analysis": analysis_data,
    }


@router.post("/{content_id}/proofread")
async def proofread(content_id: str, db: AsyncSession = Depends(get_db)):
    """
    三遍审校 — 降AI味
    对已生成的内容进行内容审校 + 去AI腔 + 节奏打磨
    借鉴 huashu-proofreading 的三遍方法论
    """
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    tags_list = content.tags.split() if content.tags else []

    # 执行三遍审校
    proofread_result = await proofread_content(
        title=content.title,
        body=content.body,
        tags=tags_list,
    )

    # 更新数据库中的内容
    content.body = proofread_result["final_body"]
    content.version += 1
    await db.commit()

    return {
        "content_id": content_id,
        "original_title": content.title,
        "original_body": content.body,
        "proofread": proofread_result,
    }
