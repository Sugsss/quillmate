"""
智能素材检索 — 借鉴 vault-curate 混合检索 + huashu-material-search 改写规范
BM25中文分词 + Hot/Cold素材分层 + 使用位置标注
"""
import re
from collections import Counter
from math import log


def tokenize_cjk(text: str) -> list:
    """
    中文分词 — 基于bigram的轻量级分词
    不需要jieba等重量依赖，对素材搜索场景足够
    """
    # 提取中文字符序列
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    tokens = []

    for segment in chinese_chars:
        # Unigram（单字，用于精确匹配）
        tokens.extend(list(segment))
        # Bigram（双字词，用于语义）
        if len(segment) >= 2:
            tokens.extend([segment[i:i+2] for i in range(len(segment)-1)])

    # 英文单词
    english_words = re.findall(r'[a-zA-Z]+', text.lower())
    tokens.extend(english_words)

    return tokens


def bm25_search(query: str, documents: list, doc_texts: list, k1: float = 1.5, b: float = 0.75) -> list:
    """
    BM25 检索算法
    借鉴 vault-curate 的混合检索思路

    query: 搜索查询
    documents: 文档ID列表
    doc_texts: 文档文本列表
    """
    if not query.strip():
        return []

    query_tokens = tokenize_cjk(query)
    if not query_tokens:
        return []

    # 分词所有文档
    tokenized_docs = [tokenize_cjk(text) for text in doc_texts]
    N = len(documents)
    avgdl = sum(len(td) for td in tokenized_docs) / max(N, 1)

    # TF per doc
    doc_tfs = []
    for td in tokenized_docs:
        cnt = Counter(td)
        doc_tfs.append(cnt)

    # IDF
    idf = {}
    for token in query_tokens:
        df = sum(1 for td in tokenized_docs if token in td)
        idf[token] = log((N - df + 0.5) / (df + 0.5) + 1) if df > 0 else 0

    # BM25 score
    scores = []
    for i, doc_id in enumerate(documents):
        score = 0.0
        doc_len = len(tokenized_docs[i])
        for token in query_tokens:
            if token not in idf:
                continue
            tf = doc_tfs[i].get(token, 0)
            if tf == 0:
                continue
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
            score += idf[token] * numerator / denominator
        if score > 0:
            scores.append((doc_id, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


class MaterialRanker:
    """
    素材排序器 — Hot/Cold 分层
    借鉴 vault-curate: Hot素材优先推荐，Cold素材定期提醒

    Hot: 最近被用于生成文案/选中的素材
    Cold: 导入后从未使用过的素材
    """

    def __init__(self):
        self.usage_counter = Counter()  # 素材使用次数
        self.last_used = {}  # 素材最后使用时间

    def mark_used(self, material_id: str):
        """标记素材被使用"""
        self.usage_counter[material_id] += 1
        from datetime import datetime
        self.last_used[material_id] = datetime.now()

    def get_hot_score(self, material_id: str) -> float:
        """
        计算 Hot 分数
        - 使用次数越多 → 越 Hot
        - 最近使用 → 更 Hot
        """
        from datetime import datetime
        count = self.usage_counter.get(material_id, 0)
        if count == 0:
            return 0.0

        last = self.last_used.get(material_id, datetime.min)
        days_since = (datetime.now() - last).days
        recency = max(0, 1.0 - days_since / 30)  # 30天内衰减到0

        return count * 0.7 + recency * 0.3

    def classify_materials(self, materials: list) -> dict:
        """
        素材分层：Hot / Warm / Cold
        """
        hot = []
        warm = []
        cold = []

        for m in materials:
            score = self.get_hot_score(m["id"])
            if score > 0.5:
                hot.append(m)
            elif score > 0:
                warm.append(m)
            else:
                cold.append(m)

        return {"hot": hot, "warm": warm, "cold": cold}


# 全局实例
ranker = MaterialRanker()
