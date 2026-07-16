---
name: insight-report
description: >
  从口播视频生成"认知提升"速读报告。当前主要支持抖音视频：先跑 Coze 工作流抓取
  视频的 ASR 口播文本，做说话人拆分，再提炼成一份 1~2 页、可每日阅读的结构化报告
  （中心思想 + 分区标签 + 精华原文 + 名言印证与批判 + 延伸应用），输出 Markdown 与
  PDF。只要用户给出抖音视频链接并想"分析/总结/提炼/做成报告/提升认知/学点东西"，
  或提到"这个视频讲了啥、帮我拆解、生成认知报告、口播 ASR"，就应使用本 skill——
  即使没有明说"报告"二字也要触发。后续会扩展到抖音以外的来源。
---

# Insight Report · 认知提升报告

把一段口播视频（当前主要是抖音）变成一份 1~2 页、能提升认知的速读报告。
核心链路：**抓取 ASR → 说话人拆分 → 四部分报告 → Markdown → PDF**。

## 目录结构

```
insight-report/
├── SKILL.md                      ← 你在这里（总流程）
├── scripts/
│   ├── fetch_douyin_asr.py       ← 跑 Coze 工作流，抓抖音 ASR 落盘
│   └── build_pdf.py              ← Markdown → PDF（含中文字体、评级方块）
├── references/
│   └── report-spec.md            ← 报告四部分的详细规格 + 完整示例（写报告前必读）
├── assets/
│   ├── .env.example              ← Coze 令牌模板，用户需复制成 .env 填写
│   └── report.css                ← PDF 样式
└── requirements.txt
```

## 何时用本 skill

用户给出抖音链接并想理解/提炼/做成报告，或直接说"生成认知报告 / 拆解这个视频 / 这段口播讲了啥"。若用户已自备 ASR 文本（不想跑抓取），跳过第 1 步，直接从第 2 步开始。

---

## 端到端流程

### 第 0 步：准备环境（首次）

安装依赖并确认 `.env` 已就绪：

```bash
cd <skill-dir>
pip install -r requirements.txt --break-system-packages -q
```

Coze 抓取需要令牌。检查是否存在 `.env`：若没有，把 `assets/.env.example` 复制为 skill 根目录下的 `.env`，让用户填入 `COZE_Personal_Access_Token`（**不要替用户编造令牌**，缺失就明确告诉用户去填）。

```bash
[ -f .env ] || cp assets/.env.example .env
```

运行前还需要两样来自用户的输入：

- **工作流 ID**（`--workflow-id`，或写进 `.env` 的 `COZE_WORKFLOW_ID`）
- **抖音视频链接**（`--douyin-url`）

若二者缺一，先向用户索要，不要瞎猜。

### 第 1 步：抓取 ASR

```bash
python scripts/fetch_douyin_asr.py \
  --workflow-id "<用户的工作流ID>" \
  --douyin-url "<抖音分享链接>" \
  --output asr_raw.txt
```

脚本会累积工作流 MESSAGE 事件的 `content` 字段（ASR 文本主要落在这里），并写入 `asr_raw.txt`。

- 若 `.env` 里设了 `COZE_WORKFLOW_ID`，可省略 `--workflow-id`。
- 若抓取为空，读脚本打印的事件日志排查（多半是工作流输出字段名、链接失效或工作流内部报错），把情况如实告诉用户，别硬编一份 ASR。
- 用户的工作流ID 默认传入：7662042950008324137

读回 `asr_raw.txt` 作为后续输入。

### 第 2 步：说话人拆分（理解用，不进正文）

通读 ASR，判断口播形态并拆分。**详细规则见 `references/report-spec.md` 的"说话人拆分"一节**，要点：

- **单播**（最常见）：一人到底 → 按句拆分、去口水词。
- **双播**：两人对谈 → 按 `A:/B:`（或身份）分轮。
- **多播**（极少）：三人及以上 → `A/B/C` 分轮。

这一步产物是"整洁的分句/分轮文本"，供你理解与后续摘录，不必全塞进报告。

### 第 3 步：写四部分报告（Markdown）

**动笔前先读 `references/report-spec.md`**，它给出每部分的精确规格和一个完整示例。四部分为：

1. **一、核心提炼** — 中心思想（引用块）+ 要点（≤3 点）+ 分区（约 5、不超 5、不过少）并给每分区打 `<span class="tag">` 标签。
2. **二、精华原文** — 从优化后的口播里截取有价值的故事/案例/整段，用 `<div class="excerpt">` 包裹，保留原味不改成白话。
3. **三、印证与批判** — 一句话总结 + 两句真实名人名言（引用块，避免纯白话）印证；先正向证明，发现纰漏则 `<div class="critique">` 批判；文末放 `<div class="rating">` 认同/不认同勾选方块。
4. **四、延伸应用** — 1~3 个方向，每方向 2~3 个具体 Case。

把报告写到 `report.md`。**成品必须能压进 1~2 页**：超长就先砍第二部分摘录数和第四部分 Case 数，保住一、三部分。

### 第 4 步：转 PDF

```bash
python scripts/build_pdf.py report.md report.pdf
```

生成后**务必核对页数**：

```bash
python3 -c "import pypdf,sys; print('页数:', len(pypdf.PdfReader('report.pdf').pages))"
```

若超过 2 页，回到 `report.md` 精简内容后重跑，直到 ≤2 页。

### 第 5 步：交付

用 `present_files` 把 `report.pdf` 和 `report.md` 一起交给用户（PDF 在前）。简短说明报告涵盖的中心思想与分区即可，不要长篇复述报告内容。

---

## 关键纪律

- **不编造**：令牌缺失、抓取失败、ASR 为空时如实说明，绝不虚构 ASR 或报告内容。
- **名言要真实**：第三部分引用的名言须真实准确、贴合思想，宁用经典不杜撰。
- **保原味**：第二部分是"摘录"不是"改写"，去口水词和轻微顺句可以，改成白话总结不行。
- **守篇幅**：1~2 页是硬约束，优先牺牲摘录与 Case 的数量。
- **可扩展**：当前抓取环节是抖音专用（Coze 工作流）；未来接入其他来源时，只需替换第 1 步的抓取脚本，产出同样的纯文本 ASR，后续流程不变。
