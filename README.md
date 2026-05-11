# Doc-to-MD Skills

[![skills.sh](https://skills.sh/b/oCOZYo/doc-to-md-skills)](https://skills.sh/oCOZYo/doc-to-md-skills)

> Three skills that convert PDF, DOCX, PPTX to Markdown — preserving diagrams, charts, and visual layouts that text-only converters lose.

[English](#english) | [中文](#中文)

---

## English

### Why these skills

Most document-to-Markdown tools either drop images entirely or OCR everything (slow, noisy, loses structure). These skills are different:

- **Zero-config Vision** — scripts extract images to disk and emit standard Markdown `![](...)` placeholders. The calling Claude Code agent describes the images using its built-in Vision capability. **No separate Anthropic API key required** — it just works with your Claude Code subscription.
- **Auto-routes by content type** — text PDFs extract instantly via `pymupdf` (seconds, zero API cost); only scanned PDFs go through OCR
- **Per-slide PPTX rendering** — every slide is rendered as a PNG and described in full, preserving spatial relationships (side-by-side comparisons, arrow directions, four-quadrant diagrams) that shape-text extraction can't capture
- **Scales to any size** — for large jobs (>5 images, or many files), the agent spawns subagents to keep image bytes out of its own context. Tested on 8,430 slides without context overflow.

For backend / cron use cases outside Claude Code, each script accepts an optional `--api-key` flag for standalone Vision processing.

### Install

```bash
npx skills add oCOZYo/doc-to-md-skills
```

Installs all three skills into the current project's `.agents/skills/`. Add `-g` to install globally for the current user, or `--skill pdf-to-md` to install just one.

### Setup

#### 1. Python environment

```bash
python3 -m venv ~/.venvs/doc-to-md
source ~/.venvs/doc-to-md/bin/activate
pip install pymupdf python-docx requests
```

#### 2. PaddleOCR (only needed for scanned PDFs)

Native-text PDFs are handled by `pymupdf` and don't need OCR. Only scanned PDFs (image-based, no text layer) trigger this path.

```bash
export PADDLEOCR_TOKEN="your_token"
export PADDLEOCR_API_URL="https://xxxx.aistudio-app.com/layout-parsing"
```

Sign up and provision an inference endpoint at https://aistudio.baidu.com/paddleocr — free tier available. After creating an endpoint, copy the URL and access token from your AI Studio dashboard.

#### 3. LibreOffice (only needed for `pptx-to-md`)

```bash
# macOS
brew install --cask libreoffice

# Debian/Ubuntu
apt install libreoffice
```

Required to convert PPTX → PDF before rendering each slide.

#### 4. (Optional) Standalone mode

For backend automation outside Claude Code:

```bash
pip install anthropic
# then pass --api-key to any script:
python pdf_to_md.py --input docs/ --output out/ --api-key sk-ant-...
```

### Usage

The skills activate automatically when you ask Claude Code to convert documents:

- *"Convert this PDF to Markdown"* → `pdf-to-md`
- *"Extract this Word doc"* → `docx-to-md`
- *"Turn these slides into notes"* → `pptx-to-md`

The agent will: run the script (deterministic extraction), then read each `![](...)` placeholder and describe it inline using its Vision capability.

Or run the scripts directly:

```bash
# PDF: auto-detect text vs scanned, extract large images
python skills/pdf-to-md/scripts/pdf_to_md.py --input docs/ --output out/

# DOCX: extract text + tables, save embedded images
python skills/docx-to-md/scripts/docx_to_md.py --input report.docx --output out/

# PPTX: render each slide as a PNG
python skills/pptx-to-md/scripts/pptx_to_md.py --input deck.pptx --output out/
```

### Skills

| Skill | Input | Method | Optional deps |
|-------|-------|--------|---------------|
| [pdf-to-md](skills/pdf-to-md/) | PDF, JPG, PNG, BMP, TIFF, WEBP | `pymupdf` direct + PaddleOCR fallback | PaddleOCR for scanned PDFs |
| [docx-to-md](skills/docx-to-md/) | DOCX | `python-docx` + extracted images | — |
| [pptx-to-md](skills/pptx-to-md/) | PPTX, PPSX | LibreOffice → PNG per slide | LibreOffice |

### License

MIT

---

## 中文

### 为什么用这套 skills

市面上的文档转 Markdown 工具，要么完全丢弃图片，要么对所有内容做 OCR（慢、噪音大、丢失结构）。这套 skills 不一样：

- **零配置 Vision** —— 脚本把图片提取到磁盘，在 Markdown 里用标准的 `![](...)` 占位符。调用方 Claude Code agent 用自带的 Vision 能力描述图片。**不需要单独申请 Anthropic API key**，用你的 Claude Code 订阅就能跑。
- **按内容类型自动分流** —— 原生文字 PDF 用 `pymupdf` 秒级提取，零 API 消耗；只有扫描 PDF 才走 OCR
- **PPTX 逐张幻灯片渲染** —— 每张幻灯片渲染成 PNG 后完整描述，保留 shape-text 提取拿不到的空间关系（左右对比、箭头方向、四象限图表）
- **任意规模可扩展** —— 大任务（>5 张图，或多文档批处理）时 agent 自动 spawn subagent，图片字节不进入主上下文。实测 8430 张幻灯片没爆上下文。

如果要在 Claude Code 外做后台自动化（cron、脚本批处理），每个脚本支持 `--api-key` 参数走 standalone 模式。

### 安装

```bash
npx skills add oCOZYo/doc-to-md-skills
```

安装全部 3 个 skill 到当前项目的 `.agents/skills/`。加 `-g` 装到用户全局目录，或 `--skill pdf-to-md` 只装一个。

### 配置

#### 1. Python 环境

```bash
python3 -m venv ~/.venvs/doc-to-md
source ~/.venvs/doc-to-md/bin/activate
pip install pymupdf python-docx requests
```

#### 2. PaddleOCR（仅扫描 PDF 需要）

原生文字 PDF 由 `pymupdf` 直接处理，不需要 OCR。只有扫描 PDF（图像形式、无文字层）会触发 OCR 路径。

```bash
export PADDLEOCR_TOKEN="your_token"
export PADDLEOCR_API_URL="https://xxxx.aistudio-app.com/layout-parsing"
```

在 https://aistudio.baidu.com/paddleocr 注册并部署一个推理服务（有免费额度）。部署完成后从 AI Studio 控制台拿到端点 URL 和访问 token。

#### 3. LibreOffice（仅 `pptx-to-md` 需要）

```bash
# macOS
brew install --cask libreoffice

# Debian/Ubuntu
apt install libreoffice
```

用于在渲染每张幻灯片前将 PPTX 转为 PDF。

#### 4.（可选）Standalone 模式

如果要在 Claude Code 外跑（后台自动化）：

```bash
pip install anthropic
# 给任何脚本加 --api-key：
python pdf_to_md.py --input docs/ --output out/ --api-key sk-ant-...
```

### 使用

在 Claude Code 里直接用自然语言触发：

- *"把这个 PDF 转成 Markdown"* → `pdf-to-md`
- *"提取这个 Word 文档"* → `docx-to-md`
- *"把这些幻灯片转成笔记"* → `pptx-to-md`

Agent 会先跑脚本做确定性提取，然后读取每个 `![](...)` 占位符，用 Vision 能力填入描述。

或直接调脚本：

```bash
# PDF：自动判断文字/扫描，提取大图到磁盘
python skills/pdf-to-md/scripts/pdf_to_md.py --input docs/ --output out/

# DOCX：提取文字+表格，保存嵌入大图
python skills/docx-to-md/scripts/docx_to_md.py --input report.docx --output out/

# PPTX：每张幻灯片渲染为 PNG
python skills/pptx-to-md/scripts/pptx_to_md.py --input deck.pptx --output out/
```

### Skill 列表

| Skill | 输入格式 | 方法 | 可选依赖 |
|-------|----------|------|----------|
| [pdf-to-md](skills/pdf-to-md/) | PDF, JPG, PNG, BMP, TIFF, WEBP | `pymupdf` 直接提取 + PaddleOCR 兜底 | PaddleOCR（扫描 PDF）|
| [docx-to-md](skills/docx-to-md/) | DOCX | `python-docx` + 抽取嵌入图 | — |
| [pptx-to-md](skills/pptx-to-md/) | PPTX, PPSX | LibreOffice → PNG 逐张渲染 | LibreOffice |

### License

MIT
