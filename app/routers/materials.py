"""
素材库路由 — 上传、列表、查看、删除
"""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.materials import Material
from app.services.parser import parse_file, count_words
from app.services.search import bm25_search, ranker
from app.services.structurer import structure_pdf, structure_pdf_to_obsidian, is_markitdown_available
from config import settings

router = APIRouter(prefix="/materials", tags=["素材库"])


@router.get("/page", response_class=HTMLResponse)
async def materials_page():
    """素材管理页面"""
    html_path = Path("app/static/materials.html")
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>页面未找到</h1>"


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    上传素材文件 — 支持 PDF / DOCX / MD / TXT
    上传后自动解析文本并存入数据库
    """
    # 1. 检查文件类型
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {ext}，支持: {settings.ALLOWED_EXTENSIONS}",
        )

    # 2. 保存文件到磁盘
    file_id = str(uuid.uuid4())
    save_name = f"{file_id}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)

    content_bytes = await file.read()
    if len(content_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 50MB 限制")

    with open(save_path, "wb") as f:
        f.write(content_bytes)

    # 3. 解析文本
    try:
        text_content = await parse_file(save_path, ext)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

    words = count_words(text_content)

    # 4. 存入数据库
    material = Material(
        id=file_id,
        title=Path(file.filename).stem,
        file_name=file.filename,
        file_type=ext,
        content=text_content,
        word_count=words,
    )
    db.add(material)
    await db.commit()

    return {
        "id": material.id,
        "title": material.title,
        "file_name": material.file_name,
        "file_type": material.file_type,
        "word_count": material.word_count,
        "preview": text_content[:300],
    }


@router.get("/list")
async def list_materials(page: int = 1, size: int = 20, db: AsyncSession = Depends(get_db)):
    """素材列表 — 分页返回，size=0 返回全部"""
    query = select(Material).order_by(Material.created_at.desc())
    
    # 先查总数
    count_query = select(func.count()).select_from(Material)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    if size > 0:
        query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    materials = result.scalars().all()
    
    return {
        "items": [
            {
                "id": m.id, "title": m.title, "file_name": m.file_name,
                "file_type": m.file_type, "word_count": m.word_count,
                "created_at": m.created_at.isoformat(), "preview": m.content[:200],
            }
            for m in materials
        ],
        "total": total, "page": page, "size": size if size > 0 else total,
        "pages": (total + size - 1) // size if size > 0 else 1,
    }


@router.get("/search")
async def search_materials(q: str = "", db: AsyncSession = Depends(get_db)):
    """素材搜索 — BM25检索 + Hot/Cold分层 + 使用位置标注"""
    if not q.strip():
        return {"results": [], "total": 0}

    result = await db.execute(select(Material).order_by(Material.created_at.desc()))
    all_materials = result.scalars().all()

    if not all_materials:
        return {"results": [], "total": 0}

    # BM25 检索
    doc_ids = [m.id for m in all_materials]
    doc_texts = [m.title + " " + m.content[:5000] for m in all_materials]
    scores = bm25_search(q, doc_ids, doc_texts)

    # 构建结果 + Hot/Cold标注
    results = []
    seen_ids = set()
    for doc_id, score in scores:
        m = next((x for x in all_materials if x.id == doc_id), None)
        if not m or m.id in seen_ids:
            continue
        seen_ids.add(m.id)

        # 使用位置标注
        content_lower = m.content.lower()
        idx = content_lower.find(q.lower())
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(m.content), idx + len(q) + 80)
            snippet = m.content[start:end]
            if start > 0: snippet = "..." + snippet
            if end < len(m.content): snippet = snippet + "..."
            ratio = idx / max(len(m.content), 1)
            usage = "开头引入" if ratio < 0.15 else ("中间案例" if ratio < 0.5 else ("深度展开" if ratio < 0.85 else "结尾升华"))
        else:
            snippet = m.content[:80]
            usage = "全文相关"

        # Hot/Cold 标注
        hot_score = ranker.get_hot_score(m.id)
        tier = "hot" if hot_score > 0.5 else ("warm" if hot_score > 0 else "cold")

        results.append({
            "material_id": m.id,
            "title": m.title,
            "file_type": m.file_type,
            "word_count": m.word_count,
            "score": round(score, 3),
            "tier": tier,
            "matches": [{"keyword": q, "snippet": snippet, "usage": usage}],
        })

    # 也包含简单 keyword 匹配的结果（BM25 没找到但 keyword 命中的）
    for m in all_materials:
        if m.id in seen_ids:
            continue
        if q.lower() in m.content.lower() or q.lower() in m.title.lower():
            idx = m.content.lower().find(q.lower())
            start = max(0, (idx if idx >= 0 else 0) - 80)
            end = min(len(m.content), (idx if idx >= 0 else 0) + len(q) + 80)
            snippet = m.content[start:end]
            hot_score = ranker.get_hot_score(m.id)
            tier = "hot" if hot_score > 0.5 else ("warm" if hot_score > 0 else "cold")
            results.append({
                "material_id": m.id,
                "title": m.title,
                "file_type": m.file_type,
                "word_count": m.word_count,
                "score": 0,
                "tier": tier,
                "matches": [{"keyword": q, "snippet": snippet, "usage": "文本匹配"}],
            })

    return {
        "q": q,
        "results": results[:20],
        "total": len(results),
        "tiers": {
            "hot": sum(1 for r in results if r["tier"] == "hot"),
            "warm": sum(1 for r in results if r["tier"] == "warm"),
            "cold": sum(1 for r in results if r["tier"] == "cold"),
        },
    }


@router.get("/{material_id}")
async def get_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """查看单个素材的完整内容"""
    result = await db.execute(
        select(Material).where(Material.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    return {
        "id": material.id,
        "title": material.title,
        "file_name": material.file_name,
        "file_type": material.file_type,
        "content": material.content,
        "word_count": material.word_count,
        "created_at": material.created_at.isoformat(),
    }


@router.delete("/{material_id}")
async def delete_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """删除素材及其文件"""
    result = await db.execute(
        select(Material).where(Material.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")

    # 删除磁盘文件
    file_path = os.path.join(settings.UPLOAD_DIR, f"{material.id}{material.file_type}")
    if os.path.exists(file_path):
        os.remove(file_path)

    await db.delete(material)
    await db.commit()
    return {"ok": True, "deleted": material.title}


@router.get("/markitdown/status")
async def markitdown_status():
    """检查 markitdown 是否可用"""
    return {"available": is_markitdown_available()}


@router.post("/{material_id}/structure")
async def structure_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """
    PDF 一键结构化 — 用 markitdown 转为 Markdown
    结果存入 Obsidian Vault 或生成新的素材记录
    """
    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")

    if material.file_type != ".pdf":
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件的结构化")

    # 找到原始 PDF 文件
    pdf_path = os.path.join(settings.UPLOAD_DIR, f"{material.id}{material.file_type}")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF 文件已被删除")

    # 执行结构化
    struct_result = structure_pdf_to_obsidian(pdf_path)

    if not struct_result.get("success"):
        raise HTTPException(status_code=500, detail=struct_result.get("error", "结构化失败"))

    # 将结构化的 .md 也作为素材入库
    import uuid as _uuid
    structured = Material(
        id=str(_uuid.uuid4()),
        title=f"{material.title}（结构化）",
        file_name=struct_result.get("filename", ""),
        file_type=".md",
        content=struct_result.get("content", ""),
        word_count=struct_result.get("word_count", 0),
    )
    db.add(structured)
    await db.commit()
    await db.refresh(structured)

    return {
        "success": True,
        "original_id": material_id,
        "structured_id": structured.id,
        "output_path": struct_result.get("output_path", ""),
        "word_count": struct_result.get("word_count", 0),
        "preview": struct_result.get("content", "")[:300],
    }
