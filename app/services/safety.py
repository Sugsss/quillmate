"""
敏感词过滤 — 借鉴 xhs-ai-writer 的 105+ 敏感词库思路
适配小红书广告法合规要求
"""
import re

# 绝对化用语（广告法禁止）
ABSOLUTE_WORDS = [
    "最", "第一", "唯一", "独家", "顶级", "极品", "极致",
    "全网第一", "全国第一", "世界第一", "销量第一", "排名第一",
    "100%", "百分百", "彻底", "完全", "绝对",
]

# 医疗/功效类（小红书重点审查）
MEDICAL_WORDS = [
    "治疗", "治愈", "疗效", "药效", "药到病除", "根治",
    "治愈率", "有效率", "无副作用", "永不复发",
]

# 过时网络语（让文案显AI味）
OUTDATED_SLANG = [
    "yyds", "绝绝子", "家人们", "谁懂啊", "咱就是说",
    "我真的会谢", "暴风哭泣", "破防了", "咱也不敢问",
]

# 机械化表达（显AI味）
MECHANICAL_WORDS = [
    "首先", "其次", "再次", "最后", "综上所述",
    "总而言之", "值得注意的是", "不可否认",
]

ALL_SENSITIVE = ABSOLUTE_WORDS + MEDICAL_WORDS + OUTDATED_SLANG + MECHANICAL_WORDS


def filter_sensitive(text: str) -> dict:
    """
    检测文本中的敏感词
    返回: {"has_issue": bool, "found": [命中的词], "suggestion": "修改建议"}
    """
    found = []
    for word in ALL_SENSITIVE:
        if word in text:
            found.append(word)

    if not found:
        return {"has_issue": False, "found": [], "suggestion": ""}

    # 给替换建议
    replace_map = {
        "最": "很/非常/超",
        "第一": "很受欢迎",
        "100%": "绝大部分",
        "绝对": "确实",
        "治疗": "改善/调理",
        "疗效": "效果",
        "yyds": "真心推荐",
        "绝绝子": "超棒",
        "家人们": "朋友们",
    }

    suggestions = []
    for w in found:
        if w in replace_map:
            suggestions.append(f"「{w}」→ 建议改为「{replace_map[w]}」")
        else:
            suggestions.append(f"「{w}」→ 建议删除或替换")

    return {
        "has_issue": True,
        "found": found,
        "suggestion": "; ".join(suggestions),
    }


def clean_content(text: str) -> str:
    """
    自动替换常见敏感词
    把「最」替换为「很」等
    """
    auto_replace = {
        "最最": "非常",
        "yyds": "真心推荐",
        "绝绝子": "超好用",
    }
    for old, new in auto_replace.items():
        text = text.replace(old, new)
    return text
