---
name: pptx-to-md
description: 将 PPTX/PPSX 演示文稿批量转换为结构化 Markdown。每张幻灯片渲染为 PNG 保存到磁盘，生成含 ![](...) 占位符的 .md 文件——由 Claude agent 用内置 Vision 能力（Read tool）填写描述，无需单独 API Key。保留流程图、架构图、对比布局、数据表格、视觉层级关系等通过文字提取会丢失的信息。当用户提到"PPTX转Markdown"、"PPT转笔记"、"演示文稿提取"、"幻灯片转md"、"PPT转Markdown"时，务必使用本 Skill。
---

# PPTX → Markdown

PPTX 中信息往往通过视觉布局（左右对比、流程图箭头、图表）呈现——单纯文字提取（如 `markitdown`）会丢失大量结构。本 Skill 将每张幻灯片渲染成 PNG，由 Claude agent 用内置 Vision 描述完整内容，能保留视觉关系。**无需单独 Anthropic API Key**。

## 流程

```
PPTX → PDF (LibreOffice) → 每页 PNG (pymupdf 150dpi) → .md 含 ![](...) 占位符 → agent 填入描述
```

## Workflow（agent 模式 — 默认，零配置）

### Step 1 — 运行渲染脚本

```bash
~/.venvs/paddleocr/bin/python \
  ~/.cc-switch/skills/pptx-to-md/scripts/pptx_to_md.py \
  --input "<pptx_or_dir>" \
  --output "<output_dir>"
```

输出：
- `<output_dir>/<stem>.md` — 每张幻灯片一段 `## Slide N`，引用对应 PNG
- `<output_dir>/<stem>/slides/slide_NNN.png` — 逐张幻灯片图片（持久保存）

示例生成的 `.md`：
```markdown
# my_deck

## Slide 1

![](my_deck/slides/slide_001.png)

## Slide 2

![](my_deck/slides/slide_002.png)
```

### Step 2 — 填写幻灯片描述

用 Read tool 读取每张 PNG，用 Edit tool 将 `![](...)` 替换为完整 Markdown 描述。**按幻灯片数量选择策略**：

- **≤ 5 张**：直接用 Read tool 逐张读取，Edit 替换占位符
- **> 5 张 / 多文件批量**：spawn subagents（每个 10–20 张）。图片字节只进 subagent 上下文，主 agent 不膨胀。实测 8,430 张不爆上下文。

  每个 subagent 的 prompt 模板：
  > 对以下 PNG 路径列表，逐一用 Read tool 读取幻灯片图片，生成 Markdown 描述：标题/副标题、正文层级、流程图节点与箭头、图表数值与坐标轴、对比布局、完整表格。返回 `[{path, description}]` JSON 数组。

  收到结果后用 Edit tool 批量替换 .md 中的占位符。大批量（数百张）时分波次 spawn，避免超并发限制。

## Standalone 模式（后台 / cron）

在 Claude Code 之外做无人值守批处理时，传 `--api-key` 让脚本自行调用 Vision API：

```bash
~/.venvs/paddleocr/bin/python \
  ~/.cc-switch/skills/pptx-to-md/scripts/pptx_to_md.py \
  --input deck.pptx --output out/ \
  --api-key sk-ant-... \
  --model claude-haiku-4-5-20251001 \
  --concurrent 5
```

也可通过环境变量统一设置模型，无需每次传 `--model`：

```bash
export DOCS_TO_WIKI_MODEL=claude-sonnet-4-6
```

询问用户选择模型（standalone 模式下）：

> 请问要用哪个 Claude 模型进行 Vision 处理？直接回车使用默认（`claude-haiku-4-5-20251001`）。

## 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--dpi` | 150 | 幻灯片渲染分辨率。文字为主用 100；密集图表用 200 |
| `--max-slides` | 200 | 单文件幻灯片数上限（费用保护） |
| `--api-key` | — | 传入则启用 standalone 模式，脚本自行调用 Vision |
| `--model` | `DOCS_TO_WIKI_MODEL` / `claude-haiku-4-5-20251001` | standalone 模式使用的 Vision 模型 |
| `--concurrent` | 5 | standalone 模式下并行 Vision 调用数 |

## 环境

- `~/.venvs/paddleocr/bin/python`：含 `pymupdf`
- LibreOffice（命令 `soffice`，macOS: `brew install --cask libreoffice`）
- `anthropic` 包 + `ANTHROPIC_API_KEY`：仅 standalone 模式（`--api-key`）需要
- `DOCS_TO_WIKI_MODEL`（可选）：standalone 模式统一覆盖模型

## 注意事项

- LibreOffice 在 macOS 下 `--convert-to png` 只导出第一张幻灯片，因此本 Skill 走 PDF→PNG 路径
- LibreOffice profile 隔离（`-env:UserInstallation`）已内建，并行运行时不会发生 lock 冲突
- 也支持 `.ppsx` 格式
- PNG 文件持久保存在 `<stem>/slides/`，agent 可在任意时间点 Read
