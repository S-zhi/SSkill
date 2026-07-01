# 双语 README 生成与同步规则

本文档定义双语 README 的生成、更新和同步方式。

---

# 1. 默认文件结构

默认生成两个 README 文件：

```text
README.md       # 中文主 README
README.en.md    # 英文 README
```

中文 README 是主版本。英文 README 应从中文 README 同步生成或更新。

---

# 2. 语言切换入口

中文 README 顶部应包含英文入口：

```md
[English](./README.en.md) | 简体中文
```

英文 README 顶部应包含中文入口：

```md
English | [简体中文](./README.md)
```

要求：

- 不要把中英文内容塞进同一个 README。
- 避免导致 README 过长。
- 保持两个 README 的章节结构一致。

---

# 3. 生成顺序

生成新 README 时：

1. 先生成 `README.md`。
2. 再根据 `README.md` 生成 `README.en.md`。
3. 保持中英文标题结构、章节顺序、代码块、链接、表格一致。

---

# 4. 增量同步规则

如果只修改中文 README 的某一节，只同步英文 README 的对应章节。

不要重新翻译整份英文 README。

示例：

```text
修改 README.md 的 “2. 快速开始”
↓
只更新 README.en.md 的 “2. Quick Start”
```

这样可以减少 Token 使用，也能避免无关内容被误改。

---

# 5. 中英文术语映射

常用标题映射：

| 中文 | 英文 |
|---|---|
| 产品介绍 | Product Overview |
| 项目定位 | Project Introduction |
| 功能展示 | Feature Showcase |
| 平台与技术支持 | Platform & Technology Support |
| 文档导航 | Documentation Navigation |
| AI 协作文档 | AI Collaboration Documents |
| 快速开始 | Quick Start |
| 安装依赖 | Install Dependencies |
| 配置环境变量 | Configure Environment Variables |
| 启动项目 | Start the Project |
| 验证启动成功 | Verify Successful Startup |
| 基础命令展示 | Basic CLI Commands |
| 配置与命令说明 | Configuration & Commands |
| 环境变量 | Environment Variables |
| 配置文件说明 | Configuration Files |
| 命令与参数说明 | Commands & Parameters |
| 系统架构与项目结构 | Architecture & Project Structure |
| 系统架构 | System Architecture |
| 项目目录结构 | Project Structure |
| 开发者指南 | Developer Guide |
| 本地开发 | Local Development |
| 提交前检查 | Pre-submission Checks |
| 云端 CI 验证 | Cloud CI Verification |
| 贡献指南 | Contributing |
| 安全漏洞报告 | Security Vulnerability Reporting |
| 版本管理 | Versioning |
| Release 与 Tag | Releases & Tags |
| 更新日志 | Changelog |
| 升级指南 | Upgrade Guide |
| 许可证 | License |
```

---

# 6. 不需要翻译的内容

以下内容通常不翻译：

- 命令行命令
- 文件名
- 环境变量名
- 配置字段名
- URL
- Badge 链接
- 代码块中的源码
- License 名称，例如 MIT、Apache 2.0
- 专有工具名，例如 Docker、GitHub Actions、Claude Code、Codex、Copilot

---

# 7. 需要同步但不强行翻译的内容

以下内容应保持含义一致，但可以根据英文 README 的阅读习惯调整表达：

- 项目介绍
- 功能说明
- 注意事项
- 贡献流程
- 安全披露说明
- 版本升级说明

---

# 8. 缺失信息处理

中文 README 中标记为“需要补充”的地方，英文 README 应翻译为：

```text
Needs User Input
```

不要在英文 README 中补造中文 README 没有的信息。

---

# 9. 同步检查清单

完成双语 README 后，应检查：

- 两个文件是否都存在。
- 两个文件是否都有语言切换入口。
- 章节结构是否一致。
- 链接是否有效。
- 代码块是否一致。
- 环境变量表是否一致。
- 命令说明是否一致。
- 安全漏洞报告方式是否一致。
- License 信息是否一致。
