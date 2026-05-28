"""
Obsidian 客户端 — 通过 Local REST API 插件读写 Vault
借鉴 vault-curate 的 Hot/Cold 分层 + obsidianRAGsody 的 RAG 思路

前提：在 Obsidian 中安装 "Local REST API" 插件
"""
import os
import re
import httpx
import yaml
from typing import Optional
from datetime import datetime, timedelta

# Obsidian Local REST API 默认端口
OBSIDIAN_API = os.getenv("OBSIDIAN_API_URL", "http://127.0.0.1:27124")
OBSIDIAN_VAULT = os.getenv("OBSIDIAN_VAULT", "")
OBSIDIAN_ENABLED = bool(OBSIDIAN_VAULT.strip())


class ObsidianClient:
    """Obsidian Local REST API 客户端"""

    def __init__(self, api_url: str = ""):
        self.api_url = api_url or OBSIDIAN_API
        self.client = httpx.AsyncClient(timeout=30)

    @property
    def enabled(self) -> bool:
        return OBSIDIAN_ENABLED

    async def check_connection(self) -> dict:
        """检查 Obsidian API 是否可用"""
        try:
            resp = await self.client.get(f"{self.api_url}/")
            if resp.status_code == 200:
                return {"connected": True, "message": "Obsidian API 已连接"}
            return {"connected": False, "message": f"API 返回 {resp.status_code}"}
        except Exception as e:
            return {
                "connected": False,
                "message": f"无法连接 Obsidian API。请在 Obsidian 中安装 'Local REST API' 插件。错误: {str(e)[:100]}",
                "setup": "Obsidian → 设置 → 第三方插件 → 社区插件市场 → 搜索 'Local REST API' → 安装并启用",
            }

    # ═══════════════════════════════════════════
    # Vault 索引
    # ═══════════════════════════════════════════

    async def list_notes(self, folder: str = "") -> list:
        """列出 vault 中所有 .md 笔记"""
        if not self.enabled:
            # 降级：直接读文件系统
            return self._list_notes_fs(folder)

        try:
            resp = await self.client.get(f"{self.api_url}/vault/", params={"path": folder})
            if resp.status_code == 200:
                files = resp.json()
                return [f for f in files if f.endswith(".md")]
        except Exception:
            pass
        return self._list_notes_fs(folder)

    def _list_notes_fs(self, folder: str = "") -> list:
        """文件系统降级方案"""
        if not OBSIDIAN_VAULT:
            return []
        import glob
        path = os.path.join(OBSIDIAN_VAULT, folder, "**", "*.md")
        return [f for f in glob.glob(path, recursive=True)]

    async def get_note(self, path: str) -> dict:
        """读取单篇笔记（含 Frontmatter 解析）"""
        try:
            if self.enabled:
                resp = await self.client.get(f"{self.api_url}/vault/{path}")
                if resp.status_code == 200:
                    content = resp.text
                else:
                    content = ""
            else:
                full_path = os.path.join(OBSIDIAN_VAULT, path)
                content = open(full_path, encoding="utf-8").read() if os.path.exists(full_path) else ""
        except Exception:
            return {"path": path, "title": path, "content": "", "tags": [], "error": "读取失败"}

        return self._parse_note(path, content)

    async def create_note(self, folder: str, filename: str, content: str, frontmatter: dict = None) -> dict:
        """在 vault 中创建新笔记"""
        # 构建带 Frontmatter 的内容
        if frontmatter:
            fm = "---\n"
            for k, v in frontmatter.items():
                if isinstance(v, list):
                    fm += f"{k}: [{', '.join(v)}]\n"
                else:
                    fm += f"{k}: {v}\n"
            fm += "---\n\n"
            content = fm + content

        path = f"{folder}/{filename}".replace("//", "/")

        try:
            if self.enabled:
                resp = await self.client.post(
                    f"{self.api_url}/vault/{path}",
                    content=content,
                    headers={"Content-Type": "text/markdown"},
                )
                if resp.status_code in (200, 201):
                    return {"created": True, "path": path}
                return {"created": False, "error": f"API 返回 {resp.status_code}: {resp.text[:200]}"}

            # 降级：直接写文件
            full_path = os.path.join(OBSIDIAN_VAULT, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"created": True, "path": path}
        except Exception as e:
            return {"created": False, "error": str(e)}

    # ═══════════════════════════════════════════
    # Frontmatter 解析
    # ═══════════════════════════════════════════

    def _parse_note(self, path: str, content: str) -> dict:
        """解析笔记的 Frontmatter 和正文"""
        frontmatter = {}
        body = content

        # 解析 YAML Frontmatter (--- ... ---)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass
                body = parts[2].strip()

        # 提取标题（优先级: frontmatter.title > 首个#标题 > 文件名）
        title = frontmatter.get("title", "")
        if not title:
            h1_match = re.search(r"^#\s+(.+)", body, re.MULTILINE)
            if h1_match:
                title = h1_match.group(1).strip()

        filename = os.path.basename(path).replace(".md", "")
        title = title or filename

        # 标签
        tags = frontmatter.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # 分类（P.A.R.A 或其他）
        folder = os.path.dirname(path)
        category = frontmatter.get("category", "")
        if not category:
            # 从路径推断分类
            if "Inbox" in folder or "00" in folder:
                category = "inbox"
            elif "Resource" in folder or "10" in folder:
                category = "resource"
            elif "Project" in folder or "20" in folder:
                category = "project"
            elif "Output" in folder or "30" in folder:
                category = "output"
            elif "Archive" in folder or "40" in folder:
                category = "archive"

        # 创建/修改时间
        created = frontmatter.get("created", frontmatter.get("date", ""))

        return {
            "path": path,
            "title": title,
            "content": body,
            "raw_content": content,
            "tags": tags,
            "category": category,
            "folder": folder,
            "created": str(created) if created else "",
            "word_count": len(body.replace("\n", "").replace(" ", "")),
        }

    async def close(self):
        await self.client.aclose()


# 全局实例
obsidian = ObsidianClient()
