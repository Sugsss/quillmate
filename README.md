# 📕 小红书 AI 内容管理系统

基于 AI 大模型驱动的内容管理与生成系统，专为小红书等内容平台设计。

**素材库 → AI 选题 → 双专家文案生成 → 发布追踪 → 数据闭环**

## ✨ 核心功能

| 模块 | 功能 |
|------|------|
| 📚 **素材库** | 上传 PDF/DOCX/MD/TXT，自动解析文本，BM25 中文检索，Hot/Cold 分层 |
| 👤 **品牌人设** | 身份/受众/风格/禁忌 4 字段配置，AI 生成时自动代入 |
| 💡 **AI 选题** | 基于素材库 + 趋势分析，4 种类型（教程/观点/拆解/清单）+ 工作量评估 |
| ✍️ **文案生成** | 双专家引擎（分析专家→创作专家），3 种开头策略，配图设计方案 |
| 🔍 **降 AI 味审校** | 三遍审校（内容→去 AI 腔→节奏打磨），借鉴 huashu-proofreading |
| 📤 **发布管理** | 文案导出 + 小红书一键发布（需 Cookie）+ 数据追踪 |
| 💬 **评论管理** | 评论采集 + AI 回复建议 + 状态管理 |
| 📊 **数据看板** | KPI 卡片 + 内容排行 + 互动率分析 |
| 💎 **Obsidian 集成** | Vault 自动索引 ↔ AI 内容写回，P.A.R.A 知识管理闭环 |

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 LLM（复制 .env.example 为 .env 并填入你的 API Key）
cp .env.example .env

# 3. 启动
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

浏览器打开 **http://127.0.0.1:8000**

## 🔧 可选集成

### Obsidian 双向同步
1. Obsidian → 社区插件 → 安装 `Local REST API`
2. `.env` 添加 `OBSIDIAN_VAULT=/你的仓库路径`
3. 访问 `/obsidian/page`

### 小红书自动发布
1. 浏览器登录 xiaohongshu.com → F12 → Application → Cookies → 复制完整 Cookie
2. `.env` 添加 `XHS_COOKIE=你的cookie`
3. 访问 `/xhs/page`

## 🏗️ 架构

```
app/
├── models/        # 6 张数据表（素材/人设/选题/内容/发布/评论）
├── routers/       # 50+ API 端点
├── services/      # LLM/解析/审校/搜索/XHS/Obsidian 客户端
├── prompts/       # AI Prompt 模板（融合多项目最佳实践）
└── static/        # 10 个前端页面
```

## 📚 借鉴的开源项目

| 项目 | Stars | 借鉴了什么 |
|------|:-----:|-----------|
| [huashu-skills](https://github.com/alchaincyf/huashu-skills) | 842⭐ | 三遍审校、素材搜索、选题方法论、开头策略 |
| [xhs-ai-writer](https://github.com/EBOLABOY/xhs-ai-writer) | 280⭐ | 双专家系统、105+敏感词库、标题公式 |
| [xhs_content_agent](https://github.com/hl897tech/xhs_content_agent) | 195⭐ | 分层架构、Prompt模板、MCP发布 |
| [XHSSpec](https://github.com/liyown/XHSSpec) | 36⭐ | 品牌人设配置、内容资产化 |
| [Spider_XHS](https://github.com/cv-cat/Spider_XHS) | 6.1k⭐ | HTTP API 数据采集 + 创作者平台发布 |
| [vault-curate](https://github.com/notoriouslab/vault-curate) | 90⭐ | Hot/Cold 素材分层、混合检索 |
| [obsidianRAGsody](https://github.com/nicolaischneider/obsidianRAGsody) | 35⭐ | RAG 查询 Vault、LlamaIndex 集成 |

## 📄 License

MIT
