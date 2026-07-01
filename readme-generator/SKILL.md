---
name: readme-generator
description: 根据项目源码、配置文件、已有文档和用户补充信息，生成或更新双语 README。用于创建 README、更新已有 README、同步 README.md 和 README.en.md。
---

# README Generator Skill

## 目标

根据项目源码、配置文件、已有文档和用户补充信息，生成或更新双语 README。

默认输出：

- `README.md`：中文主 README
- `README.en.md`：英文 README

本 Skill 的目标不是机械套模板，而是生成真正能帮助读者理解、运行、使用、开发、贡献和维护项目的 README。

---

## 核心原则

1. 优先检查项目中是否已有 README。
2. 如果已有 README，应在已有内容基础上增量修改，不要直接覆盖。
3. 中文 README 是主版本，英文 README 从中文同步生成。
4. 只修改需要修改的章节，避免整篇重写。
5. README 是项目文档入口，不是所有文档内容合集。
6. AI 文档只做链接，不把 Prompt、Skill 规则或模型专用开发指令写进 README。
7. 支持平台、依赖版本、技术栈优先使用 Shields.io Badge 展示。
8. 安全漏洞不要引导用户提交公开 Issue，应提供安全披露邮箱或 `SECURITY.md`。
9. 缺失信息必须标记为“需要补充”，不要编造。

---

## 文件索引

- `pipeline.zh.md`：README 章节结构与生成流程
- `bilingual.zh.md`：双语 README 生成与同步规则
- `update-existing.zh.md`：已有 README 的检测与增量修改规则
- `humanRead.zh.md`：向用户解释本 Pipeline 设计思路
- `templates/README.zh.template.md`：中文 README 模板
- `templates/README.en.template.md`：英文 README 模板

---

## 任务路由

### 用户要求“创建 README”

1. 读取 `pipeline.zh.md`。
2. 检查仓库是否已有 README。
3. 如果已有 README，读取 `update-existing.zh.md`。
4. 生成或更新 `README.md`。
5. 读取 `bilingual.zh.md`。
6. 同步生成或更新 `README.en.md`。

### 用户要求“更新已有 README”

1. 读取已有 `README.md` 和 `README.en.md`。
2. 读取 `update-existing.zh.md`。
3. 只修改需要变更的中文章节。
4. 根据 `bilingual.zh.md` 同步英文对应章节。
5. 不重写整篇文档。

### 用户要求“只更新某一节 README”

1. 定位中文 README 的对应章节。
2. 只修改该章节。
3. 定位英文 README 的对应章节。
4. 只同步该章节英文内容。
5. 不改动无关章节。

### 用户询问“当前 README Pipeline 的思路”

1. 读取 `humanRead.zh.md`。
2. 用简洁中文解释。
3. 不输出完整 Skill 规则，除非用户明确要求。

---

## 输出要求

生成最终文件时，应输出：

- `README.md`
- `README.en.md`

如果用户要求生成 Skill 文件，则输出当前 Skill 包中的所有文件。

生成 README 时不要输出冗长解释，除非用户要求说明修改原因。
