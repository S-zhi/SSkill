# README 生成 Pipeline

本文档定义 README 的章节结构与生成流程。

README 的定位是项目文档入口，而不是所有文档内容的堆叠。它应帮助读者按照以下路径理解项目：

> 了解项目 → 快速运行 → 学会配置和使用 → 理解结构 → 参与开发 → 贡献协作 → 查看版本与许可证

---

# 1. 产品介绍

目标：让读者在 30 秒内知道项目是什么、能做什么、是否值得继续阅读。

## 1.1 项目定位

说明：

- 这个项目是什么。
- 解决什么问题。
- 适合哪些用户或场景。

要求：

- 用简洁语言描述。
- 不堆砌技术名词。
- 不写空泛口号。
- 不把未实现能力写成已完成能力。

---

## 1.2 功能展示

优先使用已有截图、GIF、Demo 链接、流程图或功能卡片。

如果项目中没有图片资源，则用 3 到 6 个功能点概括核心能力。

要求：

- 展示最能体现项目价值的能力。
- 不列大量边缘功能。
- 不夸大项目能力。

---

## 1.3 平台与技术支持

这一节合并展示三类信息：

- 支持的平台
- 依赖版本
- 技术栈

优先使用 Shields.io Badge 展示。

示例：

```md
![Windows](https://img.shields.io/badge/Windows-supported-blue)
![macOS](https://img.shields.io/badge/macOS-supported-blue)
![Linux](https://img.shields.io/badge/Linux-supported-blue)

![Go](https://img.shields.io/badge/Go-1.24%2B-00ADD8)
![Node.js](https://img.shields.io/badge/Node.js-22%2B-339933)
![Docker](https://img.shields.io/badge/Docker-supported-2496ED)

![Gin](https://img.shields.io/badge/Gin-framework-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-4169E1)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-blue)
```

要求：

- 不要只写“使用 Go / Node / Docker”，尽量写清版本。
- 如果版本无法确定，标记为“需要补充”。
- 不展示项目实际不支持的平台。
- 技术栈用于帮助读者快速判断项目生态和学习价值。

---

## 1.4 文档导航

使用图标索引展示项目文档入口。

README 只负责导航，不负责承载所有详细内容。

推荐导航项：

```md
## 文档导航

- 🚀 [快速开始](#2-快速开始)
- ⚙️ [配置说明](#3-配置与命令说明)
- 🏗 [系统架构](#4-系统架构与项目结构)
- 📖 [API 文档](./docs/api.md)
- 📚 [技术文档](./docs/technical.md)
- 🧪 [测试文档](./docs/testing.md)
- 📄 [PRD](./docs/prd.md)
- ❓ [FAQ](./docs/faq.md)
- 🤖 [AI 协作文档](#15-ai-协作文档)
- 👥 [维护者](#维护者与帮助入口)
- 💬 [获取帮助](#维护者与帮助入口)
- 🤝 [贡献指南](#6-贡献指南)
- 🔒 [安全漏洞报告](#64-安全漏洞报告)
```

要求：

- 已存在的文档才链接。
- 不存在的文档不要生成死链接，可以标记为“需要补充”。
- “获取帮助”“维护者”“贡献指南”“安全漏洞报告”应尽量在首屏导航中出现。
- AI 文档只放入口，不展开 Prompt 内容。

---

## 1.5 AI 协作文档

README 中只说明 AI 协作文档的位置和边界。

可链接：

- `AGENTS.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `docs/ai.md`

要求：

- README 不直接写大量 AI Prompt。
- README 不承载 Skill 规则全文。
- README 只说明：AI 相关开发约束请阅读对应文件。
- 如果项目有多个 AI 文档，应说明它们分别服务于哪些工具。

示例：

```md
## AI 协作文档

本项目将 AI 协作规则拆分到独立文档中，README 仅作为入口：

- [AGENTS.md](./AGENTS.md)：通用 AI Agent / Codex 协作规则
- [CLAUDE.md](./CLAUDE.md)：Claude Code 项目上下文与开发约束
- [Copilot Instructions](./.github/copilot-instructions.md)：GitHub Copilot 仓库级说明
```

---

# 2. 快速开始

目标：让用户在最短路径内跑起项目，并确认项目确实可用。

## 2.1 安装依赖

提供依赖安装命令。

示例：

```bash
pnpm install
```

```bash
go mod tidy
```

```bash
pip install -r requirements.txt
```

要求：

- 根据项目实际技术栈生成命令。
- 如果支持多种安装方式，优先展示推荐方式。
- 不混写不适用的命令。

---

## 2.2 配置环境变量

优先使用 `.env.example`。

示例：

```bash
cp .env.example .env
```

要求：

- 不把真实密钥写进 README。
- 不让用户猜需要哪些 Token。
- 如果没有 `.env.example`，建议补充该文件。

---

## 2.3 启动项目

提供启动命令。

示例：

```bash
pnpm dev
```

```bash
go run ./cmd/server
```

```bash
docker compose up -d
```

要求：

- 优先使用项目推荐启动方式。
- 如果有前后端、数据库、任务队列等多个组件，应说明启动顺序或使用 Compose 一键启动。
- 不要只写“运行项目”。

---

## 2.4 验证启动成功

快速开始必须包含验证步骤。

根据项目类型选择：

Web 项目：

```bash
curl http://localhost:3000/api/health
```

CLI 项目：

```bash
mycli --version
mycli help
```

后端服务：

```bash
curl http://localhost:8080/health
```

Docker 项目：

```bash
docker compose ps
```

要求：

- 写清楚成功时应看到什么。
- 不让用户猜项目是否启动成功。

---

## 2.5 基础命令展示

仅 CLI 项目必须包含。

展示最小可用命令，而不是完整命令手册。

示例：

```bash
mycli init
mycli run demo.yaml
mycli status
```

要求：

- 只展示最能体现项目价值的基础命令。
- 完整命令说明放到第三章。

---

# 3. 配置与命令说明

目标：解决用户跑起来以后如何修改配置、如何使用更多能力的问题。

## 3.1 环境变量

使用表格列出环境变量。

推荐字段：

| 变量名 | 是否必填 | 默认值 | 说明 |
|---|---|---|---|

要求：

- 必填和可选变量都要写。
- 默认值要写清楚。
- 涉及敏感信息时提醒不要提交到仓库。
- 如果环境变量来自 `.env.example`，应保持一致。

---

## 3.2 配置文件说明

如果项目支持配置文件，应说明配置文件格式和路径。

例如：

- `config.yaml`
- `config.toml`
- `config.json`

要求：

- 只展示核心配置。
- 完整配置可链接到独立文档。
- 配置示例不要包含真实密钥。

---

## 3.3 命令与参数说明

将“全部命令”和“常用参数”合并说明。

要求：

- 命令和参数必须一起解释。
- 不把参数拆成孤立章节。
- 如果命令很多，可以只在 README 写常用命令，并链接到完整 CLI 文档。

---

# 4. 系统架构与项目结构

目标：帮助开发者快速理解项目如何组织。

## 4.1 系统架构

使用文字和架构图说明项目整体设计。

优先使用已有架构图。

如果没有架构图，可使用 Mermaid 简图。

要求：

- 不展开每个模块的实现细节。
- 只说明系统整体如何运转。
- 详细架构应链接到 `docs/architecture.md` 或技术文档。

---

## 4.2 项目目录结构

使用树形结构展示主要目录。

要求：

- 只解释主要目录。
- 不展开每个源文件。
- 不增加“核心模块”“数据流”“关键文件说明”等过细小节。

---

# 5. 开发者指南

目标：告诉开发者提交代码前需要做什么，以及云端会验证什么。

## 5.1 本地开发

说明开发环境准备。

要求：

- 面向参与开发的人，而不是普通使用者。
- 可以链接到更完整的开发文档。

---

## 5.2 提交前检查

说明上传代码或提交 PR 前必须执行的本地检查。

常见检查：

- 格式化：format
- 静态检查：lint
- 单元测试：unit test
- 集成测试：integration test
- 构建验证：build
- 冒烟测试：smoke test

要求：

- 尽量提供统一命令，例如 `make test`、`make check`、`pnpm check`。
- 明确哪些检查是必须的。
- 不只写“请确保代码质量”。

---

## 5.3 云端 CI 验证

说明 PR 提交后云端会自动执行哪些检查。

要求：

- 如果存在 `.github/workflows/`，应根据实际 workflow 描述。
- 如果不存在 CI，应标记“需要补充 CI 配置”。
- 说明哪些检查必须通过才能合并。

---

# 6. 贡献指南

目标：告诉外部开发者如何参与项目。

## 6.1 Issue

说明什么情况适合提交 Issue。

例如：

- Bug 反馈
- 功能建议
- 文档问题
- 使用疑问

安全漏洞不要通过公开 Issue 提交。

---

## 6.2 Pull Request

说明 PR 流程。

示例：

```md
1. Fork 本项目
2. 创建功能分支
3. 完成本地检查
4. 提交代码
5. 推送到远程分支
6. 创建 Pull Request
```

---

## 6.3 Commit 与分支规范

如果项目使用 Conventional Commits，应说明示例。

```bash
feat: 添加用户登录功能
fix: 修复配置读取失败问题
docs: 更新 README
```

要求：

- 如果已有 `CONTRIBUTING.md`，README 中只写概要并链接。
- 不把复杂贡献规则全部塞进 README。

---

## 6.4 安全漏洞报告

必须说明：安全漏洞不要提交公开 Issue。

推荐链接 `SECURITY.md`。

如果没有 `SECURITY.md`，应提供安全披露邮箱。

如果邮箱未知，标记为“需要补充安全披露邮箱”。

---

# 7. 版本管理

目标：告诉用户如何查看历史版本、更新记录，以及如何安全升级。

## 7.1 Release 与 Tag

说明项目如何发布版本。

示例：

```md
本项目通过 Git Tag 和 GitHub Releases 发布版本。

版本示例：

- v1.0.0
- v1.1.0
- v2.0.0
```

要求：

- 如果项目已有 GitHub Releases，应链接。
- 如果尚无 Release 策略，标记为“需要补充”。

---

## 7.2 更新日志

说明更新日志位置。

优先链接：

```md
[CHANGELOG.md](./CHANGELOG.md)
```

更新日志应记录：

- 新功能
- Bug 修复
- 性能优化
- 破坏性更新
- 安全修复

如果没有 `CHANGELOG.md`，标记为“需要补充更新日志”。

---

## 7.3 升级指南

如果项目存在破坏性更新，应提供升级说明。

可链接：

- `docs/upgrade.md`
- `docs/migration.md`

要求：

- 没有破坏性更新时可以省略。
- 如果存在主版本升级，例如 v1 到 v2，应说明迁移步骤。
- 不让用户升级后才发现配置、命令或 API 不兼容。

---

# 8. 许可证

目标：声明项目的使用、修改和分发规则。

要求：

- 如果存在 `LICENSE` 文件，应链接。
- 如果没有许可证，应标记为“需要补充许可证”。
- 不随意猜测许可证类型。

---

# 维护者与帮助入口

如果项目中有维护者信息，应在 README 中提供。

推荐放在文档导航附近，或贡献指南附近。

内容包括：

- 维护者姓名或组织
- 联系方式
- 讨论区
- Issue 地址
- 社区链接

如果不存在，标记为“需要补充维护者和帮助入口”。
