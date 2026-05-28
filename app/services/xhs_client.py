"""
小红书API客户端 — 数据采集 + 内容发布 + 数据追踪
集成 Spider_XHS 的 HTTP API 能力（无需浏览器，纯请求）
需要配置 XHS_COOKIE 环境变量（从浏览器登录后获取）
"""
import os
import json
import hashlib
import time
import uuid
from typing import Optional
from dataclasses import dataclass, field

import httpx

# ⚠️ Cookie 从浏览器登录小红书后 F12 → Network → 复制任意请求的 Cookie
XHS_COOKIE = os.getenv("XHS_COOKIE", "")
XHS_ENABLED = bool(XHS_COOKIE.strip())

# ── 小红书 API 端点 ──
BASE_URL = "https://edith.xiaohongshu.com"
PC_BASE = "https://www.xiaohongshu.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
}


@dataclass
class XHSNote:
    """小红书笔记"""
    note_id: str
    title: str
    desc: str
    type: str  # normal / video
    likes: int = 0
    comments: int = 0
    collects: int = 0
    shares: int = 0
    tags: list = field(default_factory=list)
    images: list = field(default_factory=list)
    author_name: str = ""
    author_id: str = ""
    publish_time: int = 0


class XHSClient:
    """
    小红书API客户端
    数据采集 + 发布 + 数据追踪，全部通过HTTP请求（无需Playwright）
    """

    def __init__(self, cookie: str = ""):
        self.cookie = cookie or XHS_COOKIE
        self.client = httpx.AsyncClient(headers=HEADERS, timeout=30)
        if self.cookie:
            self.client.cookies = self._parse_cookie(self.cookie)

    @staticmethod
    def _parse_cookie(cookie_str: str) -> dict:
        """解析Cookie字符串为字典"""
        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()
        return cookies

    @property
    def enabled(self) -> bool:
        return bool(self.cookie)

    # ═══════════════════════════════════════════
    # 数据采集
    # ═══════════════════════════════════════════

    async def search_notes(
        self, keyword: str, page: int = 1, page_size: int = 20, sort: str = "general"
    ) -> dict:
        """
        搜索小红书笔记
        sort: general(综合) / time_descending(最新) / popularity_descending(最热)
        返回: {notes: [...], total: int, has_more: bool}
        """
        if not self.enabled:
            return {"error": "未配置Cookie，无法使用小红书API", "notes": [], "total": 0}

        try:
            # 小红书搜索API
            url = f"{BASE_URL}/api/sns/web/v1/search/notes"
            params = {
                "keyword": keyword,
                "page": page,
                "page_size": min(page_size, 50),
                "sort": sort,
                "search_id": str(uuid.uuid4()),
            }
            resp = await self.client.get(url, params=params)
            data = resp.json()

            if not data.get("success"):
                return {"error": data.get("msg", "搜索失败"), "notes": [], "total": 0}

            items = data.get("data", {}).get("items", [])
            notes = []
            for item in items:
                nc = item.get("note_card", {})
                interact = nc.get("interact_info", {})
                notes.append({
                    "note_id": nc.get("note_id", ""),
                    "title": nc.get("display_title", ""),
                    "desc": nc.get("desc", "")[:200],
                    "type": nc.get("type", "normal"),
                    "likes": interact.get("liked_count", 0),
                    "comments": interact.get("comment_count", 0),
                    "collects": interact.get("collected_count", 0),
                    "tags": [t.get("name") for t in nc.get("tag_list", [])],
                    "author_name": nc.get("user", {}).get("nickname", ""),
                    "author_id": nc.get("user", {}).get("user_id", ""),
                    "cover_url": nc.get("cover", {}).get("url_default", ""),
                })

            return {
                "notes": notes,
                "total": data.get("data", {}).get("total_count", len(notes)),
                "has_more": data.get("data", {}).get("has_more", False),
            }
        except Exception as e:
            return {"error": str(e), "notes": [], "total": 0}

    async def get_note_detail(self, note_id: str) -> dict:
        """获取笔记详情（含完整内容、互动数据）"""
        if not self.enabled:
            return {"error": "未配置Cookie"}

        try:
            url = f"{BASE_URL}/api/sns/web/v1/feed"
            params = {
                "source_note_id": note_id,
                "image_formats": ["jpg", "webp", "avif"],
            }
            resp = await self.client.post(url, json=params)
            data = resp.json()

            if not data.get("success"):
                return {"error": data.get("msg", "获取失败")}

            items = data.get("data", {}).get("items", [])
            if not items:
                return {"error": "笔记不存在"}

            note = items[0].get("note_card", {})
            interact = note.get("interact_info", {})
            return {
                "note_id": note.get("note_id"),
                "title": note.get("display_title", ""),
                "desc": note.get("desc", ""),
                "type": note.get("type"),
                "views": 0,  # 小红书API不直接返回浏览量
                "likes": interact.get("liked_count", 0),
                "comments": interact.get("comment_count", 0),
                "collects": interact.get("collected_count", 0),
                "shares": interact.get("shared_count", 0),
                "tags": [t.get("name") for t in note.get("tag_list", [])],
                "images": [img.get("url_default") for img in note.get("image_list", [])],
                "publish_time": note.get("time", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_note_comments(self, note_id: str, cursor: str = "") -> dict:
        """获取笔记评论"""
        if not self.enabled:
            return {"error": "未配置Cookie", "comments": []}

        try:
            url = f"{BASE_URL}/api/sns/web/v2/comment/page"
            params = {
                "note_id": note_id,
                "cursor": cursor,
                "top_comment_id": "",
                "image_formats": ["jpg", "webp"],
            }
            resp = await self.client.get(url, params=params)
            data = resp.json()

            comments = []
            for c in data.get("data", {}).get("comments", []):
                comments.append({
                    "id": c.get("id"),
                    "content": c.get("content", ""),
                    "author": c.get("user_info", {}).get("nickname", ""),
                    "likes": c.get("like_count", 0),
                    "create_time": c.get("create_time", 0),
                })

            return {
                "comments": comments,
                "cursor": data.get("data", {}).get("cursor", ""),
                "has_more": data.get("data", {}).get("has_more", False),
            }
        except Exception as e:
            return {"error": str(e), "comments": []}

    # ═══════════════════════════════════════════
    # 趋势分析
    # ═══════════════════════════════════════════

    async def get_trending_notes(self, keyword: str, count: int = 20) -> dict:
        """
        获取热门笔记用于趋势分析
        返回热门笔记列表 + 提取的高频关键词和标签
        """
        result = await self.search_notes(keyword, page_size=count, sort="popularity_descending")
        if result.get("error"):
            return result

        notes = result.get("notes", [])

        # 提取高频标签
        tag_counter = {}
        keyword_counter = {}
        for note in notes:
            for tag in note.get("tags", []):
                tag_counter[tag] = tag_counter.get(tag, 0) + 1
            # 简单关键词提取
            for word in note.get("title", "").split():
                if len(word) >= 2:
                    keyword_counter[word] = keyword_counter.get(word, 0) + 1

        top_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "notes": notes,
            "total": result["total"],
            "trend": {
                "top_tags": [t[0] for t in top_tags],
                "top_keywords": [k[0] for k in top_keywords],
                "avg_likes": sum(n.get("likes", 0) for n in notes) // max(len(notes), 1),
                "avg_comments": sum(n.get("comments", 0) for n in notes) // max(len(notes), 1),
            },
        }

    async def extract_trend_insights(self, keyword: str) -> dict:
        """
        深度趋势分析：热门笔记 → 提取标题公式 + 内容规律 + 选题建议
        """
        result = await self.get_trending_notes(keyword, count=30)
        if result.get("error"):
            return result

        notes = result.get("notes", [])
        titles = [n.get("title", "") for n in notes[:15]]

        # 标题模式分析
        patterns = {
            "数字型": sum(1 for t in titles if any(c.isdigit() for c in t)),
            "疑问型": sum(1 for t in titles if "?" in t or "？" in t or "怎么" in t or "如何" in t),
            "感叹型": sum(1 for t in titles if "!" in t or "！" in t),
            "合集型": sum(1 for t in titles if "合集" in t or "盘点" in t or "推荐" in t),
            "教程型": sum(1 for t in titles if "教程" in t or "步骤" in t or "方法" in t or "技巧" in t),
        }

        return {
            "keyword": keyword,
            "sample_count": len(notes),
            "title_patterns": patterns,
            "trend": result.get("trend", {}),
            "sample_titles": titles[:10],
        }

    # ═══════════════════════════════════════════
    # 内容发布
    # ═══════════════════════════════════════════

    async def publish_note(
        self,
        title: str,
        content: str,
        images: list = None,
        tags: list = None,
        is_public: bool = True,
    ) -> dict:
        """
        发布小红书笔记到创作者平台

        参数:
            title: 标题（最多20字）
            content: 正文内容
            images: 图片路径列表（本地文件路径）
            tags: 话题标签列表
            is_public: 是否公开
        """
        if not self.enabled:
            return {"error": "未配置Cookie，无法发布。请设置环境变量 XHS_COOKIE", "published": False}

        try:
            # 创作者平台发布API
            url = f"{BASE_URL}/api/sns/web/v1/note"
            payload = {
                "title": title[:20],
                "desc": content,
                "type": "image" if images else "text",
                "privacy_type": "public" if is_public else "private",
                "post_time": int(time.time() * 1000),
                "topic_tags": tags or [],
            }

            if images:
                # 先上传图片
                image_ids = []
                for img_path in images:
                    img_id = await self._upload_image(img_path)
                    if img_id:
                        image_ids.append(img_id)
                payload["image_ids"] = image_ids

            resp = await self.client.post(url, json=payload)
            data = resp.json()

            if data.get("success"):
                note_id = data.get("data", {}).get("note_id", "")
                return {
                    "published": True,
                    "note_id": note_id,
                    "url": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
                    "message": "发布成功",
                }
            else:
                return {"published": False, "error": data.get("msg", "发布失败")}

        except Exception as e:
            return {"published": False, "error": str(e)}

    async def _upload_image(self, image_path: str) -> Optional[str]:
        """上传图片到小红书，返回图片ID"""
        try:
            url = f"{BASE_URL}/api/sns/web/v1/note/image"
            with open(image_path, "rb") as f:
                files = {"file": (os.path.basename(image_path), f, "image/png")}
                resp = await self.client.post(url, files=files)
            data = resp.json()
            return data.get("data", {}).get("image_id")
        except Exception:
            return None

    # ═══════════════════════════════════════════
    # 账号管理
    # ═══════════════════════════════════════════

    async def check_login(self) -> dict:
        """检查登录状态"""
        if not self.enabled:
            return {"logged_in": False, "message": "未配置Cookie"}

        try:
            url = f"{BASE_URL}/api/sns/web/v1/user/self"
            resp = await self.client.get(url)
            data = resp.json()
            if data.get("success"):
                user = data.get("data", {}).get("user_info", {})
                return {
                    "logged_in": True,
                    "user_id": user.get("user_id", ""),
                    "nickname": user.get("nickname", ""),
                    "avatar": user.get("avatar", ""),
                }
            return {"logged_in": False, "message": "登录已过期，请重新获取Cookie"}
        except Exception as e:
            return {"logged_in": False, "message": str(e)}

    async def close(self):
        await self.client.aclose()


# 全局客户端实例
xhs_client = XHSClient()
