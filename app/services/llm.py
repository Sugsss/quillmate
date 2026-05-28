"""
LLM 调用服务 — 封装大模型 API 调用
支持所有 OpenAI 兼容接口（DeepSeek / 通义千问 / Kimi / GPT 等）
换模型只需改 config.py 里的三行配置
"""
from openai import AsyncOpenAI
from config import settings

# 全局客户端实例，启动时创建一次
client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
)


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.8,
    max_tokens: int = 2000,
) -> str:
    """
    通用 LLM 调用
    - system_prompt: 系统指令（设定角色和规则）
    - user_prompt: 用户输入（具体要处理的内容）
    - temperature: 0=严谨, 1=创意（文案生成用高一些）
    """
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
