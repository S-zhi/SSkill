 ⬇️ 如何下载与安装 Skill

本项目支持通过 `npx skills` 命令行工具进行一键安装。该工具由 Vercel Labs 开源，能够自动识别并将 Skill 安装到对应的 AI 编程助手（如 Claude Code、Cursor 等）目录中。

### 基础安装

在终端中运行以下命令即可安装指定的 Skill：

```bash
npx skills add https://github.com/S-zhi/SSkill --skill <skill-name>
```

### 安装选项

您可以根据需要添加以下参数来控制安装行为：

* **安装到全局环境**：默认安装为项目级（随 Git 提交共享），添加 `-g` 可安装到用户目录，在所有项目中生效。
* **指定目标 Agent**：添加 `-a` 可指定安装给特定的 AI 工具（如 `-a claude-code` 或 `-a cursor`），支持同时指定多个。
* **非交互式安装**：添加 `-y` 可跳过所有确认提示，适用于 CI/CD 等自动化场景。

**示例：全局安装到 Claude Code 并跳过确认**

```bash
npx skills add https://github.com/S-zhi/SSkill --skill <skill-name> -g -a claude-code -y
```

> 💡 **提示**：首次运行 `npx skills` 时，系统会提示是否下载该工具包，输入 `y` 确认即可，后续会自动缓存。

​


一、Coding + Project 提效

PipeLine名称  描述 主要流程 存储地址/存储形式/调用方式 TODO&#x20;
| PipeLine名称           | 描述                                                                                                                         | 使用方式                                                                                                                                                     | 主要流程                                                                                            | 存储地址/存储形式/调用方式                                                                                                  | TODO                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| GitHub Issue Solver    | 自动检索并批量解决 GitHub 仓库的 Open Issue                                                                                  | 选择仓库打开 Agent Cli 工具，或者使用 --repo 指定仓库，指定 issue 进行解决。参数传递如下： --repo 指定仓库--issue 12,15 指定编号--skip 跳过审核确认          | 解析参数 → 寻找仓库的Open Issue → 理解项目 和 issue → 创建分支进行修改 → 绑定fix分支 → 回复修改内容 | ​[~https://github.com/S-zhi/SSkil~](https://github.com/S-zhi/SSkil)​                                                          | ​1) bug-fix ， 当前的 github-cli 不支持 包含'/'的分支绑定到 issue上。 |
| Repo Issue Hunter      | 对代码和能力两个方面进行白盒扫描，从 Bug Fix 和 Feature 两个方向找出最值得做的事，规范成标准 ISSUE，支持指定方向LIST进行扫描 | 设置定时任务，定时进行扫描                                                                                                                                   | 解析参数 →  寻找仓库的Open Issue →理解项目 → 提出Issue                                              | ​[~https://github.com/S-zhi/SSkil~](https://github.com/S-zhi/SSkil)&#xA;&#xA;资产：.ci文件是当前流程存储相关信息的缓存文件夹 | 1. 暂未补齐 INSTALL 初始化文档                                       |
|                        | ​                                                                                                                             |                                                                                                                                                              |                                                                                                     |                                                                                                                             |                                                                      |
| README Generator Skill | 根据项目源码、配置文件、已有文档和用户补充信息，生成或更新双语 README                                                        | 在项目原型进行开发时使用这个SKILL，快速搭建Readme体系，并进行项目迭代更新自定义要求：如果说当前这个项目有一些规范式的范本，那你可以进行pipeline.zh.md 替代。 | 检查是否已经有Readme → 已有就进行增量改造 → 进行文档扫描并生成必要的文件 →                          | ​[~https://github.com/S-zhi/SSkil~](https://github.com/S-zhi/SSkil)​                                                          | 流程上不是很规范 ，距离SOP有很大距离                                 |
| Repo Product Analyst   | 把一个已存在的代码仓库翻译成一份产品分析报告：它解决了什么、做到了什么程度、接下来值得做什么。                               | ​                                                                                                                                                             | 定位项目 → 建立gitnexus知识图谱 → 然后我们有一些分享的流程，然后生成按照流程生成一些网站文档。      | ​[~https://github.com/S-zhi/SSkil~](https://github.com/S-zhi/SSkil)​                                                          | 1) 没有一个很好的Quick Start&#x20;                                   |
| skill-todo             | 记录一些skill的更改                                                                                                          | ​                                                                                                                                                             | ​                                                                                                    | ​[~https://github.com/S-zhi/SSkil~](https://github.com/S-zhi/SSkil)​                                                          | ​                                                                     |


文档待完善中...