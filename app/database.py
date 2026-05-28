"""
数据库模块 — 用 SQLAlchemy 管理 SQLite
单文件数据库，备份就是一个文件拷贝，零运维
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)

# 异步会话工厂 — 每个请求拿一个 session，用完就关
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """创建所有表 — 启动时调用一次"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI 依赖注入 — 每个请求获取一个数据库会话"""
    async with async_session() as session:
        yield session
