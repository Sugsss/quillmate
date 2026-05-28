"""
文件解析服务 — 把 PDF / DOCX / Markdown / TXT 转成纯文本
"""
import io
from pathlib import Path


async def parse_file(file_path: str, file_type: str) -> str:
    """
    根据文件类型选择对应解析器，返回纯文本
    file_type: pdf / docx / md / txt
    """
    parsers = {
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
        ".md": _parse_text,
        ".txt": _parse_text,
    }
    parser = parsers.get(file_type)
    if not parser:
        raise ValueError(f"不支持的文件类型: {file_type}")
    return parser(file_path)


def _parse_pdf(file_path: str) -> str:
    """
    PDF 解析原理：
    PyPDF2 逐页读取 PDF，提取每页的文字层。
    注意：扫描版 PDF（图片）无法提取文字，需要 OCR。
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text.strip())
    return "\n\n".join(texts)


def _parse_docx(file_path: str) -> str:
    """
    Word 文档解析：
    python-docx 读取 .docx 文件，遍历所有段落提取文本。
    """
    from docx import Document

    doc = Document(file_path)
    texts = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n\n".join(texts)


def _parse_text(file_path: str) -> str:
    """纯文本/Markdown 直接读取"""
    return Path(file_path).read_text(encoding="utf-8")


def count_words(text: str) -> int:
    """简单中文字数统计"""
    return len(text.replace("\n", "").replace(" ", ""))
