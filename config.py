"""
全局配置 — 所有可调参数集中管理
换模型只需改这里的 URL 和 Key，代码一行不动
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── 服务 ──
    APP_NAME: str = "小红书AI内容管理系统"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── 数据库 ──
    DATABASE_URL: str = "sqlite+aiosqlite:///data/app.db"

    # ── LLM 大模型（OpenAI 兼容接口，换模型只改下面三行）──
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "sk-your-key-here")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # ── 文件上传 ──
    UPLOAD_DIR: str = "data/uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".md", ".txt", ".docx"}

    # ── 品牌人设 ──
    BRAND_DIR: str = "data/brand"


settings = Settings()
