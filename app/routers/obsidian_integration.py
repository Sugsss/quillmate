"""
Obsidian 集成路由 — Vault 索引、素材导入、内容写回
借鉴 vault-curate 的 Hot/Cold 分层 + huashu-material-search 的改写规范
"""
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.materials import Material
from app.models.contents import Content
from app.services.obsidian_client import obsidian, OBSIDIAN_VAULT, OBSIDIAN_ENABLED

router = APIRouter(prefix="/obsidian", tags=["Obsidian集成"])


@router.get("/status")
async def obsidian_status():
    """Obsidian 连接状态"""
    if not OBSIDIAN_ENABLED:
        return {
            "enabled": False,
            "message": "未配置 OBSIDIAN_VAULT。请在 .env 中添加: OBSIDIAN_VAULT=/你的Obsidian仓库路径",
        }
    api_status = await obsidian.check_connection()
    return {
        "enabled": True,
        "vault_path": OBSIDIAN_VAULT,
        "api": api_status,
    }


@router.get("/notes")
async def list_vault_notes(folder: str = ""):
    """浏览 vault 中的笔记列表"""
    if not OBSIDIAN_ENABLED:
        raise HTTPException(status_code=400, detail="未配置 Obsidian Vault")
    notes = await obsidian.list_notes(folder)
    return {
        "folder": folder or "root",
        "count": len(notes),
        "notes": notes[:100],  # 截断避免太大
    }


@router.get("/notes/{path:path}")
async def get_vault_note(path: str):
    """读取单篇笔记详情（含 Frontmatter 解析）"""
    if not OBSIDIAN_ENABLED:
        raise HTTPException(status_code=400, detail="未配置 Obsidian Vault")
    return await obsidian.get_note(path)


@router.post("/import")
async def import_from_vault(data: dict, db: AsyncSession = Depends(get_db)):
    """
    从 Obsidian Vault 导入笔记到素材库

    请求体:
    {"folder": "10-Resources", "limit": 20}  - 导入指定文件夹
    {"paths": ["10-Resources/社交沟通.md"]}   - 导入指定笔记
    {"all": true}                             - 全量导入
    """
    if not OBSIDIAN_ENABLED:
        raise HTTPException(status_code=400, detail="未配置 Obsidian Vault")

    folder = data.get("folder", "")
    paths = data.get("paths", [])
    all_vault = data.get("all", False)
    limit = data.get("limit", 50)

    imported = 0
    skipped = 0

    if paths:
        note_paths = paths
    elif all_vault:
        note_paths = await obsidian.list_notes()
        note_paths = note_paths[:limit]
    else:
        note_paths = await obsidian.list_notes(folder)
        note_paths = note_paths[:limit]

    for note_path in note_paths:
        # 检查是否已导入（按文件路径去重）
        existing = await db.execute(
            select(Material).where(Material.title == note_path)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        note = await obsidian.get_note(note_path)
        if note.get("error"):
            continue

        import uuid
        material = Material(
            id=str(uuid.uuid4()),
            title=note["title"],
            file_name=os.path.basename(note_path),
            file_type=".md",
            content=note["content"],
            word_count=note.get("word_count", 0),
        )
        db.add(material)
        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped, "total": len(note_paths)}


@router.post("/export")
async def export_to_vault(data: dict, db: AsyncSession = Depends(get_db)):
    """
    将生成的文案写回 Obsidian Vault

    请求体:
    {"content_id": "xxx", "folder": "30-Output"}
    """
    if not OBSIDIAN_ENABLED:
        raise HTTPException(status_code=400, detail="未配置 Obsidian Vault")

    content_id = data.get("content_id", "")
    folder = data.get("folder", "30-Output")

    # 获取内容
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    tags_list = content.tags.split() if content.tags else []

    # 生成文件名
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = content.title[:40].replace("/", "-").replace(":", "-")
    filename = f"{date_str} {safe_title}.md"

    # 构建带 Frontmatter 的正文
    full_content = content.body
    if content.image_suggestion:
        full_content += f"\n\n> 📷 配图建议: {content.image_suggestion}"

    result = await obsidian.create_note(
        folder=folder,
        filename=filename,
        content=full_content,
        frontmatter={
            "title": content.title,
            "tags": tags_list,
            "date": date_str,
            "platform": content.platform,
            "source": "AI内容系统",
        },
    )

    return result


@router.get("/folders")
async def list_folders():
    """列出 vault 的文件夹结构（用于 P.A.R.A 导航）"""
    if not OBSIDIAN_ENABLED:
        raise HTTPException(status_code=400, detail="未配置 Obsidian Vault")

    folders = set()
    notes = await obsidian.list_notes()
    for n in notes:
        folder = os.path.dirname(n)
        if folder:
            folders.add(folder)

    # P.A.R.A 默认结构
    para = {
        "inbox": any("Inbox" in f or "00" in f for f in folders),
        "resources": any("Resource" in f or "10" in f for f in folders),
        "projects": any("Project" in f or "20" in f for f in folders),
        "output": any("Output" in f or "30" in f for f in folders),
        "archive": any("Archive" in f or "40" in f for f in folders),
    }

    return {
        "folders": sorted(folders),
        "para_detected": para,
        "total_notes": len(notes),
    }
