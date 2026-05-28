"""
三遍审校服务 — 借鉴 huashu-proofreading 降AI味方法论
优化：加超时保护、降级处理、错误透传
"""
from app.services.llm import call_llm

# ── 第一遍：内容审校 ──
PASS1_SYSTEM = """你是一名专业的内容编辑，负责第一遍审校——内容质量检查。

检查维度：事实准确性、逻辑链、结构合理性、信息密度。

输出 JSON（不要 markdown 代码块）：
{"issues": ["问题描述"], "fixed": "修正后的正文", "changes_summary": "一句话说明"}
如果没有问题，issues 为空数组，fixed 为原文。"""

# ── 第二遍：降AI味 ──
PASS2_SYSTEM = """你是小红书博主，负责去AI腔。
禁止：首先其次再次、值得注意的是、综上所述、yyds、绝绝子、家人们。
改写：书面语→口语、长句→短句、机械结构→自然段落、抽象→具体画面。
注入：真实感受、可以吐槽可以不确定。

输出 JSON：{"fixed": "去AI味后的正文", "changes": ["改动1","改动2"]}"""

# ── 第三遍：节奏打磨 ──
PASS3_SYSTEM = """你是排版编辑，负责最后一轮节奏打磨。
短句(5-10字) + 中句(15-25字) + 偶尔长句交替。段落不等长。适量emoji。读出声来，卡顿处改顺。

输出 JSON：{"fixed": "打磨后的正文", "changes": ["打磨了什么"]}"""


async def proofread_content(title: str, body: str, tags: list) -> dict:
    """三遍审校主流程，每遍独立容错，失败不阻断后续"""
    import json, asyncio

    result = {
        "pass1": {"issues": [], "summary": "未执行"},
        "pass2": {"changes": []},
        "pass3": {"changes": []},
        "final_title": title,
        "final_body": body,
        "final_tags": tags,
        "improvement_count": 0,
    }

    full_text = f"标题：{title}\n\n正文：{body}"
    current_body = body

    # ── 第一遍：内容审校（90s超时）──
    try:
        raw1 = await asyncio.wait_for(
            call_llm(PASS1_SYSTEM, full_text, temperature=0.3, max_tokens=1500),
            timeout=90
        )
        p1 = _parse_json(raw1)
        result["pass1"] = {
            "issues": p1.get("issues", []),
            "summary": p1.get("changes_summary", "完成"),
        }
        current_body = p1.get("fixed", current_body)
        result["improvement_count"] += len(p1.get("issues", []))
    except asyncio.TimeoutError:
        result["pass1"] = {"issues": [], "summary": "⏱ 超时跳过"}
    except Exception as e:
        result["pass1"] = {"issues": [], "summary": f"跳过: {str(e)[:50]}"}

    # ── 第二遍：降AI味（90s超时）──
    try:
        raw2 = await asyncio.wait_for(
            call_llm(PASS2_SYSTEM, f"原标题：{title}\n\n{current_body}", temperature=0.7, max_tokens=1500),
            timeout=90
        )
        p2 = _parse_json(raw2)
        result["pass2"] = {"changes": p2.get("changes", [])}
        current_body = p2.get("fixed", current_body)
        result["improvement_count"] += len(p2.get("changes", []))
    except asyncio.TimeoutError:
        result["pass2"] = {"changes": [], "error": "⏱ 超时跳过"}
    except Exception as e:
        result["pass2"] = {"changes": [], "error": f"跳过: {str(e)[:50]}"}

    # ── 第三遍：节奏打磨（仅正文>200字时执行，90s超时）──
    if len(current_body) > 200:
        try:
            raw3 = await asyncio.wait_for(
                call_llm(PASS3_SYSTEM, current_body, temperature=0.5, max_tokens=1000),
                timeout=90
            )
            p3 = _parse_json(raw3)
            result["pass3"] = {"changes": p3.get("changes", [])}
            current_body = p3.get("fixed", current_body)
            result["improvement_count"] += len(p3.get("changes", []))
        except asyncio.TimeoutError:
            result["pass3"] = {"changes": [], "error": "超时跳过"}
        except Exception as e:
            result["pass3"] = {"changes": [], "error": f"跳过: {str(e)[:50]}"}
    else:
        result["pass3"] = {"changes": [], "error": "正文较短，跳过节奏打磨"}

    result["final_body"] = current_body
    return result


def _parse_json(raw: str) -> dict:
    """安全解析LLM返回的JSON"""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    import json
    return json.loads(cleaned)
