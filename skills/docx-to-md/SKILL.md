---
name: docx-to-md
description: 将 DOCX/Word 文档批量转换为结构化 Markdown。直接提取标题、段落、表格（python-docx，无损），并将嵌入大图保存到磁盘，生成含 ![](...) 占位符的 .md 文件——由 Claude agent 用内置 Vision 能力（Read tool）填写描述，无需单独 API Key。保留架构图、流程图、截图等通过文字提取会丢失的信息。当用户提到"DOCX转Markdown"、"Word转笔记"、"提取Word内容"、"docx转md"、"Word文档转换"时，务必使用本 Skill。
---

# DOCX → Markdown

DOCX 是结构化 XML，文字可以直接无损提取，无需 OCR；但嵌入图片（架构图、流程图、截图）若占比较大，图文关系本身是信息。本 Skill 将图片提取到磁盘，由 Claude agent 用内置 Vision 描述完整内容，能保留视觉关系。**无需单独 Anthropic API Key**。

## 流程

```
DOCX → python-docx 提取文字/表格 → 图片保存磁盘 → .md 含 ![](...) 占位符 → agent 填入描述
```

## Workflow（agent 模式 — 默认，零配置）

### Step 1 — 运行提取脚本

```bash
~/.venvs/paddleocr/bin/python \
  ~/.cc-switch/skills/docx-to-md/scripts/docx_to_md.py \
  --input "<docx_or_dir>" \
  --output "<output_dir>"
```

输出：
- `<output_dir>/<stem>.md` — 标题/段落/表格按原顺序排列，图片位置有 `![](...)` 占位符
- `<output_dir>/<stem>/imgs/img_NNN.{ext}` — 提取的嵌入图片（持久保存）

示例生成的 `.md`：
```markdown
# 项目说明

这是第一段正文。

![](my_doc/imgs/img_001.png)

| 列A | 列B |
|-----|-----|
| 数据1 | 数据2 |
```

### Step 2 — 填写图片描述

用 Read tool 读取每张图片，用 Edit tool 将 `![](...)` 替换为完整 Markdown 描述。**按图片数量选择策略**：

- **≤ 5 张**：直接用 Read tool 逐张读取，Edit 替换占位符
- **> 5 张 / 多文件批量**：spawn subagents（每个 10–20 张）。图片字节只进 subagent 上下文，主 agent 不膨胀。

  每个 subagent 的 prompt 模板：
  > 对以下图片路径列表，逐一用 Read tool 读取图片，生成 Markdown 描述：说明图片内容、流程图节点与箭头、图表数值与坐标轴、对比布局、完整表格。返回 `[{path, description}]` JSON 数组。

  收到结果后用 Edit tool 批量替换 .md 中的占位符。

## Standalone 模式（后台 / cron）

在 Claude Code 之外做无人值守批处理时，传 `--api-key` 让脚本自行调用 Vision API：

```bash
~/.venvs/paddleocr/bin/python \
  ~/.cc-switch/skills/docx-to-md/scripts/docx_to_md.py \
  --input file.docx --output out/ \
  --api-key sk-ant-... \
  --model claude-haiku-4-5-20251001
```

也可通过环境变量统一设置模型：

```bash
export DOCS_TO_WIKI_MODEL=claude-sonnet-4-6
```

询问用户选择模型（standalone 模式下）：

> 请问要用哪个 Claude 模型进行 Vision 处理？直接回车使用默认（`claude-haiku-4-5-20251001`）。

## 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--large-image-kb` | 30 | 图片 blob 超过此值（KB）才提取/描述。30KB 默认能过滤掉徽标/图标 |
| `--no-images` | — | 纯文字模式，跳过所有图片，零 API 消耗 |
| `--max-images` | 50 | 单文档图片数上限（费用保护） |
| `--api-key` | — | 传入则启用 standalone 模式，脚本自行调用 Vision |
| `--model` | `DOCS_TO_WIKI_MODEL` / `claude-haiku-4-5-20251001` | standalone 模式使用的 Vision 模型 |

## 环境

- `~/.venvs/paddleocr/bin/python`：含 `python-docx`
- `anthropic` 包 + `ANTHROPIC_API_KEY`：仅 standalone 模式（`--api-key`）需要
- `DOCS_TO_WIKI_MODEL`（可选）：standalone 模式统一覆盖模型，例如 `export DOCS_TO_WIKI_MODEL=claude-sonnet-4-6`

## 注意事项

- 仅对原生 `.docx` 有效；遗留 `.doc` 需先用 LibreOffice 转换：
  `soffice --headless --convert-to docx file.doc`
- 不处理 EMF/WMF 等矢量格式（python-docx 不直接暴露），主要识别 PNG/JPEG/GIF/BMP/WEBP 嵌入图
- 图片文件持久保存在 `<stem>/imgs/`，agent 可在任意时间点 Read
