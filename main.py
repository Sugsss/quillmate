"""
小红书AI内容管理系统 — 主入口
融合三个 GitHub 项目的精华：
- xhs_content_agent 的分层架构
- xhs-ai-writer 的双专家 prompt
- XHSSpec 的品牌人设思路
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from config import settings
from app.database import init_db
from app.routers import materials, brand, topics, contents, publish, analytics, comments, xhs_integration, obsidian_integration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库，关闭时清理资源"""
    await init_db()
    print(f"✅ 数据库初始化完成")
    print(f"📕 {settings.APP_NAME} 启动在 http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API文档: http://{settings.HOST}:{settings.PORT}/docs")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI驱动的小红书内容管理：素材库 → 选题推荐 → 文案生成 → 发布追踪",
    version="0.1.0",
    lifespan=lifespan,
)

# ── 静态文件 ──
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── 页面路由（必须在API路由之前注册，否则 /{content_id} 会拦截 /page）──

@app.get("/", response_class=HTMLResponse)
async def page_index():       return _read_html("index.html")
@app.get("/topics/page", response_class=HTMLResponse)
async def page_topics():      return _read_html("topics.html")
@app.get("/contents/page", response_class=HTMLResponse)
async def page_contents():    return _read_html("contents.html")
@app.get("/publishes/page", response_class=HTMLResponse)
async def page_publishes():   return _read_html("publishes.html")
@app.get("/comments/page", response_class=HTMLResponse)
async def page_comments():    return _read_html("comments.html")
@app.get("/analytics/page", response_class=HTMLResponse)
async def page_analytics():   return _read_html("dashboard.html")
@app.get("/xhs/page", response_class=HTMLResponse)
async def page_xhs():         return _read_html("xhs.html")
@app.get("/obsidian/page", response_class=HTMLResponse)
async def page_obsidian():    return _read_html("obsidian.html")


# ── 注册 API 路由 ──
app.include_router(materials.router)
app.include_router(brand.router)
app.include_router(topics.router)
app.include_router(contents.router)
app.include_router(publish.router)
app.include_router(analytics.router)
app.include_router(comments.router)
app.include_router(xhs_integration.router)
app.include_router(obsidian_integration.router)


def _read_html(filename: str) -> str:
    with open(f"app/static/{filename}", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
