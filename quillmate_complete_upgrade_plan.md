# Quillmate 完整升级方案

> 目标: 在保留原项目核心架构的前提下,实现从单体应用到插件化架构的平滑进化。
> 原则: 每阶段只改 1-3 个文件,每阶段结束都是可运行的完整版本。

---

## 一、版本演进路线

```
Day 0   Day 1    Day 2    Day 3    Day 4    Day 5    Day 6    Day 7    Day 8    Day 9    Day 10
  |       |        |        |        |        |        |        |        |        |         |
v0.0 -> v0.1 -> v0.2 -> v0.3 -> v0.4 -> v0.5 -> v0.6 -> v0.7 -> v0.8 -> v0.9 -> v1.0
  |       |        |        |        |        |        |        |        |        |         |
基础    图片     多模型    Prompt   扫码     数据     抽象     服务     批量     插件     配置
设施    素材     路由     模板化   登录     回流     接口     定位器   工作流   基类     驱动
```

| 版本 | 改动文件 | 时间 | 核心价值 |
|------|---------|------|---------|
| v0.1 | 3 新增, 2 修改 | 1h | JPG/PNG/扫描PDF 结构化 |
| v0.2 | 1 新增, 1 修改 | 30min | 多模型路由降成本 |
| v0.3 | 5 新增, 1 修改 | 1h | Prompt 可配置 |
| v0.4 | 1 新增, 1 修改 | 1h | 扫码登录替代 Cookie |
| v0.5 | 1 新增, 2 修改 | 1h | 数据自动回流 Obsidian |
| v0.6 | 2 新增 | 2h | 抽象接口层 |
| v0.7 | 1 新增, 3 修改 | 2h | 服务定位器 |
| v0.8 | 1 新增 | 2h | 批量工作流引擎 |
| v0.9 | 2 新增 | 2h | 插件基类 + 管理器 |
| v1.0 | 3 新增, 3 修改 | 3h | 配置驱动 + 内置插件重构 |

---

## 二、Day 0: 基础设施 (一次性准备)

### 2.1 新增文件

| 文件 | 作用 |
|------|------|
| `utils/feature_flags.py` | 功能开关中心,所有新功能默认关闭 |
| `utils/registry.py` | 服务注册表,Phase 1 管理服务,Phase 3 变为插件注册中心 |

### 2.2 设计要点

- 所有新功能通过 `ENABLE_XXX=true/false` 控制
- 开关未启用时,原项目代码完全不受影响
- 注册表支持延迟初始化,避免循环依赖

---

## 三、Day 1: v0.1 素材处理流水线

### 3.1 目标

让 Quillmate 能处理 **JPG/PNG/扫描版PDF/EPUB/MOBI/AZW3** 六种格式。

### 3.2 新增文件

| 文件 | 作用 |
|------|------|
| `services/asset_processors/base.py` | 素材处理器抽象基类 |
| `services/asset_processors/image_processor.py` | 图片处理: Tesseract OCR 兜底 + GPT-4o 多模态主力 |
| `services/asset_processors/pdf_processor.py` | PDF 处理: 文字版直接提取,扫描版转图片走 vision |
| `services/asset_processors/ebook_processor.py` | 电子书处理: EPUB 直接解析,MOBI/AZW3 用 Calibre 转 EPUB |
| `services/asset_pipeline.py` | 素材流水线统一入口,管理所有处理器 |

### 3.3 修改文件

| 文件 | 修改内容 |
|------|---------|
| `services/ai_engine.py` | 新增 `vision_analyze()` 方法: 接收图片路径,返回结构化 Markdown |
| `main.py` | 条件注册 `/api/v1/assets/process` 和 `/api/v1/assets/batch` 路由 |
| `.env` | 新增 `ENABLE_ASSET_PIPELINE=true`, `VISION_MODEL=gpt-4o` |

### 3.4 处理流程

```
用户上传文件 -> AssetPipeline 识别后缀 -> 路由到对应 Processor

JPG/PNG: ImageProcessor -> Tesseract OCR 兜底 -> GPT-4o vision 主力 -> 结构化 Markdown

文字版 PDF: PDFProcessor -> PyMuPDF 提取文本 -> 直接返回

扫描版 PDF: PDFProcessor -> PyMuPDF 逐页转图片 -> AssetPipeline 调用 vision_analyze 逐页识别 -> 合并 Markdown

EPUB: EbookProcessor -> ebooklib 解析章节 -> BeautifulSoup 清理 HTML -> 合并 Markdown

MOBI/AZW3: EbookProcessor -> Calibre 转换为 EPUB -> 走 EPUB 流程
```

### 3.5 输出格式

所有素材处理后统一输出到 Obsidian `01 Resources/` 目录,文件格式:

```markdown
---
source: "原文件名.jpg"
type: "image"
processed_at: "2026-05-30T10:00:00"
status: "structured"
tags: []
---

# 结构化内容标题

...正文...

## 关联笔记

- [[ ]]

## 我的思考

> 待补充...
```

### 3.6 验证方式

```bash
curl -X POST "http://localhost:8000/api/v1/assets/process"   -F "file_path=/path/to/test.jpg"

# 返回: {"success": true, "obsidian_path": "01 Resources/test_jpg.md"}
```

---

## 四、Day 2: v0.2 AI 多模型路由

### 4.1 目标

不同任务自动选择最优模型,降低 API 成本。

### 4.2 新增文件

| 文件 | 作用 |
|------|------|
| `services/ai_router.py` | 任务路由器,根据任务类型选择模型 |

### 4.3 修改文件

| 文件 | 修改内容 |
|------|---------|
| `services/ai_engine.py` | 原有 `chat()` 不变,新增 `_chat_with_model()` 支持指定模型 |
| `.env` | 新增模型配置: `WRITING_MODEL`, `ANALYSIS_MODEL`, `PROOF_MODEL`, `CHEAP_MODEL` |

### 4.4 路由策略

| 任务类型 | 默认模型 | 用途 |
|---------|---------|------|
| vision | gpt-4o | 图片理解 |
| analysis | claude-3-5-sonnet | 深度分析 |
| writing | deepseek-chat | 文案生成 |
| proofreading | claude-3-5-sonnet | 审校 |
| cheap | deepseek-chat | 标签提取、简单总结 |

### 4.5 成本对比

| 模型 | 输入 $/M tokens | 输出 $/M tokens |
|------|----------------|----------------|
| gpt-4o | 5.0 | 15.0 |
| claude-3-5-sonnet | 3.0 | 15.0 |
| deepseek-chat | 0.5 | 2.0 |

使用路由后,写作类任务成本降低约 90%。

---

## 五、Day 3: v0.3 Prompt 模板化

### 5.1 目标

双专家/审校的 Prompt 外置为可编辑文件,不用改代码就能调风格。

### 5.2 新增文件

| 文件 | 作用 |
|------|------|
| `utils/prompt_manager.py` | Jinja2 模板加载器,支持变量渲染 |
| `prompts/xiaohongshu/expert_analyst.j2` | 分析师 Prompt 模板 |
| `prompts/xiaohongshu/expert_writer.j2` | 创作者 Prompt 模板 |
| `prompts/xiaohongshu/proofreading_v1.j2` | 质量检查 Prompt |
| `prompts/xiaohongshu/proofreading_v2.j2` | 去 AI 味 Prompt |
| `prompts/xiaohongshu/proofreading_v3.j2` | 节奏优化 Prompt |
| `prompts/system/asset_structuring.j2` | 素材结构化 Prompt |

### 5.3 修改文件

| 文件 | 修改内容 |
|------|---------|
| `services/content_gen.py` | 硬编码 Prompt -> `prompt_manager.load()` 加载模板 |
| `services/proofreading.py` | 同上,三阶段审校分别加载对应模板 |

### 5.4 模板变量示例

expert_writer.j2 支持变量:
- `{{ persona.role }}` - 博主身份
- `{{ persona.audience }}` - 目标受众
- `{{ persona.style }}` - 风格定位
- `{{ persona.taboos }}` - 内容禁忌
- `{{ analysis }}` - 上游分析结果
- `{{ title_formula }}` - 标题公式

### 5.5 验证方式

修改 `prompts/xiaohongshu/expert_writer.j2`,重启服务,生成风格立即变化。

---

## 六、Day 4: v0.4 小红书扫码登录

### 6.1 目标

替代手动复制 Cookie,支持浏览器扫码登录,Cookie 加密自动保存。

### 6.2 新增文件

| 文件 | 作用 |
|------|------|
| `services/xhs_auth.py` | Playwright 扫码登录 + Fernet 加密存储 |

### 6.3 修改文件

| 文件 | 修改内容 |
|------|---------|
| `services/xhs_publisher.py` | 从环境变量读取 Cookie -> 调用 `xhs_auth.get_session()` |
| `main.py` | 新增 `/api/v1/xhs/login-qr` 和 `/api/v1/xhs/login-status` 路由 |

### 6.4 安全设计

- Cookie 用机器指纹派生密钥加密存储
- 存储文件 `.xhs_session.enc`,无法直接读取
- 过期后自动提示重新扫码

### 6.5 验证方式

```bash
# 触发扫码
curl -X POST "http://localhost:8000/api/v1/xhs/login-qr"
# 浏览器弹出,手机小红书扫码

# 检查状态
curl "http://localhost:8000/api/v1/xhs/login-status"
# {"logged_in": true}
```

---

## 七、Day 5: v0.5 数据自动回流

### 7.1 目标

每小时自动同步小红书浏览/点赞/评论/收藏数据回 Obsidian。

### 7.2 新增文件

| 文件 | 作用 |
|------|------|
| `tasks/sync_task.py` | APScheduler 定时任务,每小时执行一次 |

### 7.3 修改文件

| 文件 | 修改内容 |
|------|---------|
| `services/obsidian_sync.py` | 新增 `update_metadata()`: 只更新 YAML frontmatter,不改动正文 |
| `main.py` | 启动时注册定时器,新增 `/api/v1/sync/trigger` 手动触发接口 |
| `models.py` | 新增 `PublishRecord` 表,记录发布内容和平台 ID |

### 7.4 回流数据格式

Obsidian 笔记 frontmatter 自动更新:

```yaml
---
xhs_views: 1250
xhs_likes: 89
xhs_collects: 34
xhs_comments: 12
last_synced: "2026-05-30T11:00:00"
---
```

---

## 八、Day 6-7: v0.6-v0.7 抽象层

### 8.1 目标

为插件化做准备,定义接口 + 服务定位器。

### 8.2 新增文件

| 文件 | 作用 |
|------|------|
| `core/interfaces.py` | 三大接口: `IAssetProcessor`, `IAIModel`, `IPlatformPublisher` |
| `core/adapters.py` | 适配器: 将原有代码包装为接口实现 |
| `core/service_locator.py` | 服务定位器: 运行时获取服务实例 |

### 8.3 接口定义

```python
IAssetProcessor:
  - supported_extensions: list
  - extract(file_path) -> {text, metadata}

IAIModel:
  - name: str
  - chat(prompt) -> str
  - vision(image_path, prompt) -> str

IPlatformPublisher:
  - platform_name: str
  - authenticate(credentials) -> bool
  - publish(content) -> {success, url}
  - get_analytics(content_id) -> {views, likes}
```

### 8.4 与原项目的衔接

原有代码不需要改,通过 Adapter 实现接口:

```
AIEngine (原有) -> LegacyAIAdapter -> 实现 IAIModel
ImageProcessor (v0.1) -> LegacyImageProcessorAdapter -> 实现 IAssetProcessor
XHSPublisher (原有) -> LegacyPublisherAdapter -> 实现 IPlatformPublisher
```

---

## 九、Day 8: v0.8 批量工作流引擎

### 9.1 目标

一键批量处理: 5 张图 -> 5 篇文案 -> 5 次发布。

### 9.2 新增文件

| 文件 | 作用 |
|------|------|
| `services/workflow_engine.py` | 工作流引擎: 异步任务队列 + 状态机 |

### 9.3 工作流状态

```
PENDING -> PROCESSING -> COMPLETED
                |
                v
             FAILED
```

### 9.4 API

```bash
# 创建工作流
POST /api/v1/workflow/create
  name: "weekly_batch"
  asset_paths: "/path/1.jpg,/path/2.jpg,/path/3.jpg"
  persona: {"role": "科技博主", "style": "硬核干货"}
  auto_publish: false

# 返回: {"job_id": "a1b2c3d4"}

# 查询状态
GET /api/v1/workflow/{job_id}/status
# 返回: {"status": "processing", "progress": 0.6, "results": [...]}
```

---

## 十、Day 9-10: v0.9-v1.0 插件化内核

### 10.1 目标

新增平台/模型只需实现接口,无需改核心代码。

### 10.2 新增文件

| 文件 | 作用 |
|------|------|
| `plugins/base.py` | 插件基类: `Plugin`, `AssetPlugin`, `AIPlugin`, `PlatformPlugin` |
| `plugins/manager.py` | 插件管理器: 自动发现、注册、生命周期管理 |
| `plugins/builtin/xiaohongshu_plugin.py` | 小红书内置插件 |
| `plugins/builtin/image_plugin.py` | 图片处理内置插件 |
| `plugins/builtin/deepseek_plugin.py` | DeepSeek 模型内置插件 |
| `config/plugins.yaml` | 插件配置: 启用/禁用、参数、路由规则 |

### 10.3 插件配置示例

```yaml
plugins:
  builtin:
    - name: xiaohongshu
      enabled: true
      config:
        auto_publish: false

    - name: image_processor
      enabled: true
      config:
        ocr_enabled: true

  custom:
    - name: wechat_official
      module: plugins.custom.wechat_plugin
      enabled: false

routing:
  vision: gpt-4o
  analysis: claude
  writing: deepseek
```

### 10.4 新增平台只需 4 个方法

```python
class WeChatPlugin(PlatformPlugin):
    @property
    def platform_name(self): return "wechat"

    async def authenticate(self, credentials): ...
    async def publish(self, content): ...
    async def get_analytics(self, content_id): ...
```

---

## 十一、Docker 部署

### 11.1 Dockerfile

基于 `python:3.11-slim`,预装:
- Tesseract OCR (中文/英文)
- Calibre (电子书转换)
- Playwright Chromium (扫码登录)

### 11.2 docker-compose.yml

```yaml
services:
  quillmate:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ${OBSIDIAN_VAULT}:/vault:ro
      - quillmate_data:/data
      - ./.env:/app/.env:ro
      - ./.xhs_session.enc:/app/.xhs_session.enc

  ollama:  # 可选本地模型
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: [ollama_models:/root/.ollama]
```

---

## 十二、依赖清单

```txt
# 原有
fastapi, uvicorn, sqlalchemy, httpx, aiohttp, python-dotenv

# 素材处理
PyMuPDF, pytesseract, Pillow, ebooklib, beautifulsoup4, lxml

# 模板 + 任务 + 安全 + 扫码 + YAML
Jinja2, apscheduler, cryptography, playwright, PyYAML
```

系统依赖:
```bash
# macOS
brew install tesseract tesseract-lang
brew install --cask calibre

# Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-chi-sim calibre
```

---

## 十三、回滚策略

每个版本独立开关,随时回滚:

```bash
# 回滚到原项目
ENABLE_ASSET_PIPELINE=false
ENABLE_AI_ROUTER=false
ENABLE_PROMPT_TEMPLATES=false
ENABLE_XHS_QR_LOGIN=false
ENABLE_DATA_SYNC=false
ENABLE_WORKFLOW_ENGINE=false
ENABLE_PLUGIN_SYSTEM=false
```

---

## 十四、今晚就能跑的最小启动包

### 步骤 (共 20 分钟)

1. **安装依赖** (2 min)
   ```bash
   pip install Pillow pytesseract
   # macOS: brew install tesseract tesseract-lang
   ```

2. **创建目录** (1 min)
   ```bash
   mkdir -p services/asset_processors utils
   ```

3. **复制 5 个新文件** (5 min)
   - `utils/feature_flags.py`
   - `utils/registry.py`
   - `services/asset_processors/base.py`
   - `services/asset_processors/image_processor.py`
   - `services/asset_pipeline.py`

4. **修改 2 个文件** (5 min)
   - `services/ai_engine.py`: 新增 `vision_analyze()` 方法
   - `main.py`: 条件注册素材处理路由

5. **配置环境变量** (1 min)
   ```bash
   echo "ENABLE_ASSET_PIPELINE=true" >> .env
   echo "VISION_MODEL=gpt-4o" >> .env
   ```

6. **测试** (1 min)
   ```bash
   python -m uvicorn main:app --reload
   curl -X POST "http://localhost:8000/api/v1/assets/process"      -F "file_path=/path/to/test.jpg"
   ```

看到结构化 Markdown 返回 = 成功,可以继续 Day 2。
