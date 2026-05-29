"""
PDF 结构化服务 — 基于 PyPDF2 + AI 实现
将 PDF 文本提取后用 AI 重新结构化为 Markdown，保留标题、要点、章节
"""
import os

from app.services.obsidian_client import OBSIDIAN_VAULT
from app.services.parser import _parse_pdf, count_words


def is_markitdown_available() -> bool:
    """检查 markitdown CLI 是否可用"""
    import subprocess
    try:
        result = subprocess.run(["markitdown", "--help"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def structure_pdf(pdf_path: str, output_dir: str = "") -> dict:
    """
    PDF 结构化：先用 PyPDF2 提取文本，再用 AI 添加结构

    返回: {"success": bool, "output_path": str, "content": str, "error": str}
    """
    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"文件不存在: {pdf_path}"}

    if not pdf_path.lower().endswith(".pdf"):
        return {"success": False, "error": "仅支持 PDF 文件"}

    # 用 PyPDF2 提取文本
    try:
        raw_text = _parse_pdf(pdf_path)
    except Exception as e:
        return {"success": False, "error": f"PDF 解析失败: {str(e)}"}

    if not raw_text.strip():
        return {"success": False, "error": "PDF 无可提取文本（可能是扫描版）"}

    # 输出路径
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    md_name = f"{base}.md"

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, md_name)
    else:
        output_path = os.path.join(os.path.dirname(pdf_path), md_name)

    # 保存提取的文本（暂时保留原始文本，后续可加 AI 结构化）
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    return {
        "success": True,
        "output_path": output_path,
        "filename": md_name,
        "content": raw_text,
        "word_count": count_words(raw_text),
    }


def structure_pdf_to_obsidian(pdf_path: str) -> dict:
    """
    将 PDF 结构化后写入 Obsidian Vault（与原始 PDF 同目录）
    这样 Obsidian 里 PDF 旁边就有一份结构化的 .md
    """
    if not OBSIDIAN_VAULT:
        return {"success": False, "error": "未配置 Obsidian Vault"}

    # 判断 pdf_path 是否在 vault 内
    if pdf_path.startswith(OBSIDIAN_VAULT):
        # vault 内的 PDF → 同目录生成 .md
        rel_dir = os.path.dirname(pdf_path)
        return structure_pdf(pdf_path, rel_dir)
    else:
        # vault 外的 PDF → 存到 vault 的 Resources 目录
        resources = os.path.join(OBSIDIAN_VAULT, "10-Resources")
        return structure_pdf(pdf_path, resources)
