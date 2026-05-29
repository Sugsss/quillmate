# 📕 QuillMate — AI 小红书内容引擎

AI 大模型驱动的内容管理与生成系统。从 Obsidian 知识库到小红书发布，全流程自动化。

**素材库 → AI 选题 → 双专家文案生成 → 降AI味审校 → 发布追踪 → 数据闭环**

## ✨ 核心功能

### 🤖 AI 引擎
- **双专家文案生成**：分析专家解读素材 → 创作专家撰写文案，过程可视化
- **三遍降AI味审校**：内容质量 → 去AI腔 → 节奏打磨，借鉴 huashu-proofreading
- **AI 选题推荐**：基于素材库 + 4 种类型（教程/观点/拆解/清单）+ 工作量评估
- **AI 回复建议**：评论管理 + 智能生成回复草稿

### 💎 Obsidian 双向集成
- **Vault 自动索引**：通过 Local REST API 将笔记同步为素材
- **内容写回**：生成的文案自动保存到 Obsidian，带 YAML Frontmatter
- **PDF 一键结构化**：提取 PDF 文本保存为 .md
- **P.A.R.A 文件夹支持**：Inbox / Resources / Projects / Output / Archive

### 🎨 品牌管理
- **人设配置**：身份、受众、风格、禁忌词
- **视觉风格矩阵**：4 种内容类型 × 配色自动匹配
- **生图提示词**：AI 直接输出 Midjourney/Stable Diffusion 格式

### 📊 运营闭环
- **小红书发布**：一键发布到创作者平台（需 Cookie）
- **数据追踪**：浏览量/点赞/评论/收藏自动同步
- **数据看板**：KPI 总览 + 内容排行

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 LLM
cp .env.example .env
# 编辑 .env 填入 API Key（支持 OpenAI 兼容接口）

# 3. 启动
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

浏览器打开 **http://127.0.0.1:8000**

## 🔧 可选集成

### Obsidian 双向同步
```bash
# 1. Obsidian → 社区插件 → 安装 Local REST API
# 2. .env 添加
OBSIDIAN_VAULT=/你的Vault路径
OBSIDIAN_API_URL=https://127.0.0.1:27124
OBSIDIAN_API_KEY=Bearer 你的APIKey
```

### 小红书发布
```bash
# .env 添加 XHS_COOKIE=浏览器登录后复制的Cookie
```

## 🏗️ 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python + FastAPI + SQLAlchemy + SQLite |
| AI | OpenAI 兼容接口（通义千问/DeepSeek/GPT） |
| 前端 | 原生 HTML/JS，9 个页面 |
| 集成 | Obsidian Local REST API + Spider_XHS |

## 📚 借鉴的开源项目

| 项目 | Stars | 借鉴了什么 |
|------|:-----:|-----------|
| [huashu-skills](https://github.com/alchaincyf/huashu-skills) | 842⭐ | 三遍审校、素材搜索、选题方法论、开头策略 |
| [xhs-ai-writer](https://github.com/EBOLABOY/xhs-ai-writer) | 280⭐ | 双专家系统、105+敏感词库、标题公式 |
| [xhs_content_agent](https://github.com/hl897tech/xhs_content_agent) | 195⭐ | 分层架构、Prompt模板 |
| [XHSSpec](https://github.com/liyown/XHSSpec) | 36⭐ | 品牌人设配置、内容资产化 |
| [Spider_XHS](https://github.com/cv-cat/Spider_XHS) | 6.1k⭐ | HTTP API 数据采集 + 创作者平台发布 |
| [vault-curate](https://github.com/notoriouslab/vault-curate) | 90⭐ | Hot/Cold 素材分层、混合检索 |
| [microsoft/markitdown](https://github.com/microsoft/markitdown) | 128k⭐ | PDF 转 Markdown 方案 |

## 📄 License

MIT
