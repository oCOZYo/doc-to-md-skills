---
name: pdf-to-md
description: 将 PDF 文件批量转换为结构化 Markdown。自动识别原生文字 PDF（pymupdf 直接提取，秒级完成，无需 API Key）和扫描/图像 PDF（PaddleOCR 云端识别）。原生 PDF 中的嵌入大图保存到磁盘，由 Claude agent 用内置 Vision 描述（无需 API Key）。也支持 JPG/PNG/BMP/TIFF/WEBP 图片文件。当用户提到以下任意场景时，务必使用本 Skill：（1）文档转换类："PDF转Markdown"、"扫描PDF"、"图像PDF"、"图片文档"、"OCR提取"、"处理一批PDF"、"文档转Markdown"、"文档转笔记"；（2）PDF内容提取/解析类："读取这个PDF"、"解析PDF"、"提取PDF内容"、"PDF里有什么"、"帮我看看这个PDF"、"从PDF中提取数据"、"分析这份PDF"；（3）用户提供了一个 PDF 文件路径或刚下载了 PDF，并希望获取其中的文字或数据内容。
---

# PDF / 图片 → Markdown

## 格式路由

| 输入 | 路径 | 说明 |
|------|------|------|
| PDF（原生文字，平均 >50 字符/页） | `pdf_to_md.py` (pymupdf) | 秒级完成，无 API 消耗 |
| PDF（扫描 / 图像） | `ocr_extract.py` (PaddleOCR 云端) | 自动识别后跳过快速路径 |
| 图片（JPG / PNG / BMP / TIFF / WEBP） | `ocr_extract.py` | 仅 PaddleOCR 路径 |

---

## Workflow（agent 模式 — 默认，零配置）

### Step 1：原生文字 PDF 快速提取

先对所有 PDF 跑快速提取——原生文字 PDF 直接出结果（嵌入大图保存到磁盘留占位符），扫描 PDF 自动跳过：

```bash
~/.venvs/general/bin/python \
  ~/.cc-switch/skills/pdf-to-md/scripts/pdf_to_md.py \
  --input "<source_dir_or_file>" \
  --output "<output_dir>"
```

输出每个文件的状态：
- `text (avg NNN ch/pg, N images extracted)` — 已提取，结果在 `<output_dir>/<stem>.md`
- `scanned (avg N ch/pg)` — 跳过，进入 Step 2

嵌入图片输出：
- `<output_dir>/<stem>.md` — 正文中图片位置有 `![](...)` 占位符
- `<output_dir>/<stem>/imgs/img_NNN.{ext}` — 提取的图片（持久保存）

可选参数：
- `--large-image-kb 30`：嵌入大图超过此值才提取（过滤小图标）
- `--no-images`：纯文字模式，跳过所有图片
- `--max-images 50`：单文档图片数上限

如果只有图片文件（非 PDF），跳过此步直接进 Step 2。

### Step 1b — 填写图片描述（有嵌入图片时）

用 Read tool 读取每张图片，用 Edit tool 将 `![](...)` 替换为完整 Markdown 描述。

- **≤ 5 张**：直接用 Read tool 逐张读取，Edit 替换占位符
- **> 5 张**：spawn subagents（每个 10–20 张），图片字节只进 subagent 上下文

### Step 2：OCR（扫描 PDF + 图片）

> `ocr_extract.py` 与 `pdf_to_md.py` 是两个独立脚本，接口不同：
> `ocr_extract.py` 使用**位置参数**（无 `--input/--output` 标志）。

```bash
export PADDLEOCR_TOKEN="your_token"
export PADDLEOCR_API_URL="https://xxxx.aistudio-app.com/layout-parsing"
python3 ~/.cc-switch/skills/pdf-to-md/scripts/ocr_extract.py \
  "<source_dir>" "<output_dir>"
```

OCR 输出结构：
- `per_page/`：逐页独立 MD（仅云端多页时生成）
- `merged/`：全文合并 MD，适合直接导入知识库

### Step 3：可选审查与调整

如果用户要求调整格式（修正识别错误、统一术语、优化标题层级），先读取 `references/optimization-prompt.md` 中的处理规范，再用 `Edit` 工具针对性修改。

## Standalone 模式（后台 / cron）

在 Claude Code 之外做无人值守批处理时，传 `--api-key` 让脚本自行调用 Vision API 描述嵌入图片：

```bash
~/.venvs/paddleocr/bin/python \
  ~/.cc-switch/skills/pdf-to-md/scripts/pdf_to_md.py \
  --input file.pdf --output out/ \
  --api-key sk-ant-... \
  --model claude-haiku-4-5-20251001
```

也可通过环境变量统一设置模型：

```bash
export DOCS_TO_WIKI_MODEL=claude-sonnet-4-6
```

询问用户选择模型（standalone 模式下）：

> 请问要用哪个 Claude 模型进行 Vision 处理？直接回车使用默认（`claude-haiku-4-5-20251001`）。

## 环境

- `~/.venvs/general/bin/python`：含 `pymupdf`
- `PADDLEOCR_TOKEN` / `PADDLEOCR_API_URL`：云端 OCR 凭证（仅 Step 2 需要）
- `anthropic` 包 + `ANTHROPIC_API_KEY`：仅 standalone 模式（`--api-key`）需要
- `DOCS_TO_WIKI_MODEL`（可选）：standalone 模式统一覆盖模型，例如 `export DOCS_TO_WIKI_MODEL=claude-sonnet-4-6`

## 注意事项

- 原生文字 PDF 走快速路径：无 API 消耗，秒级完成
- Token 含个人凭证，始终用环境变量传入，不要写在命令行
- 图片文件持久保存在 `<stem>/imgs/`，agent 可在任意时间点 Read
- 本地 MLX VLM 模式：`ocr_extract.py` 支持 `--server_url`，详见脚本 `--help`
