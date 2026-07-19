# 安装并配置 GitNexus

**何时读本文件**：Phase 1 里 `check_graph.py` 报告 `gitnexus_installed: false`，或执行 `npx gitnexus analyze` 失败（缺 node、安装崩溃、命令找不到）时。按本文档装好即可建图；实在装不上再走文末的**降级方案**，不要卡死。

GitNexus 把代码库用 Tree-sitter 索引成本地知识图谱，供后续用图谱查询替代逐文件阅读，显著降低分析的 Token 成本。它**完全本地运行**，代码不出机器。

---

## 前置：Node.js
GitNexus 通过 npm 分发，需要本机有 **Node.js 与 npm**（建议较新的 LTS，如 20/22）。
```bash
node -v && npm -v   # 有输出即已安装
```
没有的话：macOS `brew install node`；或用 nvm 装 LTS（`nvm install --lts`）；Windows 用 winget `winget install OpenJS.NodeJS.LTS`。

---

## 安装方式（二选一）

### 方式 1：免安装，直接 npx（最省事）
在**仓库根目录**运行：
```bash
npx gitnexus analyze
```
一条命令会走完多阶段索引流水线（Structure → Tree-sitter 解析 → 跨文件 Resolution → 聚类 → 执行流 → 检索索引），并把图谱存到仓库内的 `.gitnexus/`。中型项目通常一分钟内完成。

### 方式 2：全局安装（常用可固定版本）
```bash
npm install -g gitnexus
gitnexus analyze          # 之后可直接用 gitnexus 命令
```

### npm 11.x 的已知坑
`npx gitnexus` 在 npm 11.x 下可能崩溃（报 `Cannot destructure property 'package' of 'node.target'`）。改用 pnpm 形式绕过：
```bash
pnpm --allow-build=@ladybugdb/core --allow-build=gitnexus --allow-build=tree-sitter dlx gitnexus@latest analyze
```

---

## 验证索引成功
```bash
gitnexus status    # 当前仓库索引状态
gitnexus list      # 已索引的全部仓库
```
建图成功后，别忘了在本 Skill 里写复用标记：
```bash
python3 <skill>/scripts/check_graph.py --mark
```

---

## 配置 MCP（可选但推荐，让 Claude Code 直接查图谱）
配好后可用 `query / context / impact / detect_changes / cypher` 等图谱工具，成本远低于逐文件读。

自动配置（自动探测编辑器并写入全局 MCP 配置，跑一次即可）：
```bash
npx gitnexus setup
# 只配指定编辑器： npx gitnexus setup -c claude-code
```

或手动为 Claude Code 添加：
```bash
# macOS / Linux
claude mcp add gitnexus -- npx -y gitnexus@latest mcp
# Windows
claude mcp add gitnexus -- cmd /c npx -y gitnexus@latest mcp
```

> ⚠️ `gitnexus setup` / `claude mcp add` 会写入全局或编辑器配置，属于会留下持久改动的操作，**执行前先向用户确认**（Skill 调用时若带了 `--skip` 参数则跳过这次确认，直接配置）。

---

## 常用命令速查
| 命令 | 作用 |
|---|---|
| `npx gitnexus analyze` | 从仓库根建/更新索引 |
| `gitnexus analyze --force` | 全量重建（大改动后） |
| `gitnexus status` / `list` | 查看索引状态 / 已索引仓库 |
| `npx gitnexus setup` | 一次性配置编辑器 MCP |
| `gitnexus uninstall` | 预览移除 GitNexus 的 MCP/skills/hooks |

图谱会过期：仓库有较大改动后，分析前先重新 `analyze` 一次，否则影响面/调用链会与 HEAD 不一致（`check_graph.py` 会据 HEAD 变化提示 rebuild）。

---

## 降级方案（GitNexus 实在装不上 / 离线 / 缺 node）
**不要卡死。** 跳过图谱，改为手动探索，后续 Phase 照常执行，只是证据来自人工阅读而非图谱：
- 读 `README` / `docs`、列目录树；
- 看包管理清单（package.json / pyproject.toml / go.mod 等）与依赖；
- 定位入口文件与核心模块，抽样阅读关键代码；
- 保持“证据优先”：Bug/Feature 的结论仍要挂到具体文件/函数。
