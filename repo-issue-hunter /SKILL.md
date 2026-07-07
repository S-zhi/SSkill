---
name: repo-issue-hunter
description: 分析一个【已有的代码仓库】，从 Bug Fix 和 Feature 两个方向找出最值得做的问题，规范化成标准 issue，并用 GitHub 官方 API 创建到仓库里；所有已创建的 issue 会被压缩记录到 .ci 文件夹用于去重，避免重复建单。当用户说“帮这个项目提 issue / 找 bug / 提需求 / 看看有什么该修该做的 / 自动建 issue / 扫一遍仓库开工单”，或希望把一个仓库的改进点系统性地落成 GitHub issue 时，就应主动使用本 Skill——即使用户没明说“建 issue”也要触发。它与 repo-product-analyst 互补：那个产出分析报告，这个产出并创建可执行的 issue。Use this whenever the user wants to scan a repository for bugs / feature gaps and file them as GitHub issues via the official API, with .ci-based dedup so nothing gets created twice.
---

# Repo Issue Hunter（仓库 → 标准 issue → 官方 API 建单，带 .ci 去重）

把一个**已存在的代码仓库**扫一遍，从 **Bug Fix** 和 **Feature** 两个方向找出最值得做的事，规范成标准 issue，经用户确认后用 **GitHub 官方 API** 创建，并把结果**压缩记录到 `.ci` 文件夹**，保证下次执行不会重复建单。

**贯穿始终的四条原则：**
- **`.ci` 先行**：Skill 一被触发，第一件事就是读当前仓库的 `.ci` 文件夹，拿到“已经建过哪些 issue / 是否已建过图谱”，后续所有判断都建立在这个已知状态之上。
- **证据优先**：每个 Bug / Feature 结论都尽量挂上具体代码证据（文件 / 模块 / 函数 / 入口）。说不清来源的不写。
- **幂等与安全**：本地验证代码必须幂等、绝不造成数据丢失或污染；任何涉及模型调用 / 有计费的测试，跑之前先向用户确认。建 issue 前必须经用户明确同意。
- **语言跟随用户**：issue 正文与对话默认用用户当前语言（中文用户输出中文）。

---

## 总体流程

严格按 Phase 0 → Phase 6 顺序执行。脚本都在 `scripts/`，从**仓库根目录**运行（`python <skill>/scripts/xxx.py ...`）。

### Phase 0 — 加载即读 `.ci`（启动引导，必做）

1. 定位仓库根目录：`git rev-parse --show-toplevel`。所有后续命令都 `cd` 到这里。
2. 运行引导脚本，初始化并读取 `.ci`：
   ```bash
   python <skill>/scripts/ci_bootstrap.py
   ```
   它会（不存在则创建、已存在则只读）输出一份 JSON 状态：`.ci` 是否就绪、图谱是否已建、**已创建过哪些 issue（类型 / 标题 / 编号 / URL）**。
3. 把“已创建 issue 列表”记在脑子里——**它是本轮去重的基线**。后面任何候选 issue 都要先和它比对，重复的直接丢弃。
   > `.ci/` 是在用户自己仓库里建的本地文件夹，属常规本地写入，无需额外确认；但“建 issue、改全局配置”等副作用操作仍要确认。`.ci` 的结构与去重机制见 `references/ci-folder.md`。

### Phase 1 — 建立 / 复用知识图谱（GitNexus）

先建图谱、再做分析：直接读全部源码又慢又烧 Token，先用 GitNexus 把代码库索引成知识图谱，之后用图谱查询精准定位，只读真正需要的部分。

1. 判断是否需要重新建图（避免重复建图）：
   ```bash
   python <skill>/scripts/check_graph.py
   ```
   - 输出 `skip` → 图谱新鲜（`.ci` 里记的 HEAD 与当前一致），**直接复用，不要重建**。
   - 输出 `rebuild` → 没建过 / 代码已变，需要建图。
   - 若输出里 `gitnexus_installed: false`（或 `npx gitnexus analyze` 报命令找不到 / 崩溃）→ **先读 `references/setup-gitnexus.md` 装好并配置**（含 npm 11 的 pnpm 绕过、MCP 配置）；装完再建图。实在装不上，直接走该文档末尾的**降级方案**，不要卡死。
2. 需要建图时，在仓库根目录执行：
   ```bash
   npx gitnexus analyze
   ```
   - 若 npm 11.x 下 `npx` 安装崩溃：
     `pnpm --allow-build=@ladybugdb/core --allow-build=gitnexus --allow-build=tree-sitter dlx gitnexus@latest analyze`
   - 建完后写入标记，供下次复用：
     ```bash
     python <skill>/scripts/check_graph.py --mark
     ```
3. 探索优先用 GitNexus MCP 工具（成本远低于逐文件读）：`query "<概念>"` 定位代码簇、`context <符号>` 看 360° 视图、`impact <符号>` 看影响面、`cypher "<图查询>"` 挖架构关系。
   > **降级方案**（GitNexus 跑不起来 / 离线 / 缺 node）：不要卡死。改为手动探索——读 README、列目录树、看包管理清单、定位入口与核心模块、抽样读关键代码。后续 Phase 照常，只是证据来自人工阅读。

### Phase 2 — 双轨分析：Bug Fix 与 Feature

围绕图谱，从两个方向各自产出候选。**每条都要挂代码证据。**

#### 轨道 A：Bug Fix（修 Bug）
用图谱定位可疑点：缺失/错误的异常处理、边界与空值、并发与竞态、资源泄漏、契约不一致（接口与实现/文档不符）、错误的默认值、明显的逻辑漏洞等。

**本地验证的授权与红线**——允许写“类似单测”的代码在本地跑来确认 bug，但必须遵守：
- **严格幂等**：同一段验证代码反复跑，结果一致、不留副作用。
- **绝不破坏数据**：禁止运行任何会写生产数据、删除文件、改动外部状态（真实数据库/线上服务/用户文件）的测试。一律用临时目录、内存态、fixture 或 mock。
- **付费 / 模型调用要先确认**：任何会触发真实模型调用、外部 API 计费、或产生消费的验证，**跑之前先明确告诉用户成本并征得同意**，不要擅自执行。
- 拿不准某个验证是否安全 → 默认不跑，先问。

对每个 bug，先在脑子里把“现象 / 触发条件 / 期望 vs 实际 / 根因 / 证据”想清楚，为 Phase 4 的格式化做准备。

#### 轨道 B：Feature（加新特性）
**用产品思维提，不要为技术而技术。** 每个 Feature 先回答两问：
- **为什么需要这个能力**：它对应哪个用户 / 什么场景 / 解决什么痛点，为什么现在值得做。说不出“为什么”的想法直接砍掉。
- **实现可能性**：现有架构是否支撑、大致改动量、主要风险或依赖。别提空中楼阁。

### Phase 3 — 反思与收敛（最多 5 个）

**这是进入建单前的闸门，必须做。**
1. 逐条反思合理性：是不是真问题？证据够不够硬？价值是否真的成立？Feature 的“为什么”站得住吗？——把牵强的、证据不足的、价值存疑的剔除掉。
2. 与 Phase 0 的**已创建 issue 列表去重**：语义上重复的（哪怕措辞不同）一律丢弃。
3. 反思后若剩下的 issue **超过 5 个**，按 `影响 × 紧急/成本` 选出**最重要的 5 个**（Bug 与 Feature 混合排序，不必两边均分）。反思后觉得都没问题且不超 5 个，就全部保留。
4. **只有通过反思后，才进入 Phase 4**。若一个都不成立，如实告诉用户“本轮没有值得新建的 issue”，结束。

### Phase 4 — 规范化输出格式

严格套用 `references/issue-formats.md` 的模板（那里有完整格式 + 示例）。要点：

- **Bug Fix**
  - 标题：`【Bug Request】<一句话写清具体是什么问题>`
  - 正文三部分：① Bug 的具体问题 ② 相关配置 ③ 修复建议
- **Feature**
  - 标题：`【Feature】<一句话写清具体是什么需求>`
  - 正文两部分：① 简单说明为什么要实现 ② 从用户故事角度分析解决了什么问题、能带来什么收益

把每个 issue 的最终标题 + 正文准备好（建议写到临时文件，便于 `--body-file` 传入）。

### Phase 5 — 用官方 API 创建 issue（**需用户明确确认**）

创建 issue = 在（可能公开的）仓库里发布内容，属于不可轻易撤销的副作用操作，**必须先经用户同意**。

1. **先空跑**，把最终清单和去重结果摆给用户看：
   ```bash
   python <skill>/scripts/create_issue.py --dry-run \
     --type bug --title "…" --body-file /tmp/issue1.md
   ```
   `--dry-run` 会做完本地 + 远端去重检查、打印将要创建什么，但**不调用 API、不写记录**。对每个候选都空跑一遍，然后把“将创建 N 条 issue：标题列表 + 正文预览 + 去重结论”呈现给用户。
2. **等用户明确说“可以创建 / 确认”后**，再逐条真正创建（去掉 `--dry-run`）：
   ```bash
   python <skill>/scripts/create_issue.py \
     --type bug --title "…" --body-file /tmp/issue1.md
   ```
   鉴权见 `references/github-api.md`：优先用已登录的 `gh` CLI，否则用环境变量 `GITHUB_TOKEN`（需要 issues 写权限）。仓库默认从 `git remote origin` 自动识别，也可 `--repo owner/name` 显式指定。
   - 若空跑结果里 `auth: null`（既没装/没登录 `gh`，也没有 `GITHUB_TOKEN`）→ **先读 `references/setup-gh.md`**，按里面任一方案（装并登录 `gh`，或只配 `GITHUB_TOKEN`）配好鉴权再建单。
3. 若用户没确认、或鉴权实在配不上，**不要创建**，把 issue 内容直接给用户，让他自己建，并说明缺什么（`gh` 登录 / `GITHUB_TOKEN`，指向 `references/setup-gh.md`）。

### Phase 6 — 压缩记录到 `.ci`（自动，保证幂等）

`create_issue.py` 创建成功后会**自动**把这条 issue 压缩成一条指纹记录（`fingerprint + 类型 + 标题 + 编号 + URL + 时间`），追加到 `.ci/issues/created.jsonl`（可加 `--gzip` 额外产出 `.gz` 压缩快照）。

这带来天然幂等：下次再跑本 Skill，Phase 0 读到这些记录、Phase 3/Phase 5 的去重就会自动跳过已建的 issue，不会重复创建。**不要手动改 `.ci/issues/` 里的记录文件**——它是去重的真相来源。

---

## 结束前的自检清单

- [ ] Phase 0 真的读了 `.ci`，拿到了已创建 issue 基线？
- [ ] 图谱是复用还是新建，判断依据是 `check_graph.py` 而不是拍脑袋？
- [ ] 每个 Bug/Feature 都挂了代码证据？本地验证守住了幂等 + 不破坏数据 + 付费先确认？
- [ ] 反思收敛到 ≤5 个，且和 `.ci` 已建列表去重过？
- [ ] 格式严格套了 `references/issue-formats.md` 的模板？
- [ ] 建单前**空跑 + 用户确认**都做了？
- [ ] 建成功的 issue 都进了 `.ci`？（`create_issue.py` 会自动做，确认没报错即可）

---

## 参考文件（按需读取）

- `references/issue-formats.md` —— Bug Fix / Feature 的完整格式模板与示例（Phase 4 必读）。
- `references/github-api.md` —— `gh` CLI 与 GitHub REST API 建单的鉴权、用法、去重与错误处理（Phase 5 必读）。
- `references/setup-gh.md` —— `gh` 安装与鉴权配置（当 `gh` 未装/未登录且无 `GITHUB_TOKEN` 时读）。
- `references/setup-gitnexus.md` —— GitNexus 安装与配置（当 `gitnexus`/`npx` 缺失或建图失败时读，含降级方案）。
- `references/ci-folder.md` —— `.ci` 文件夹结构、指纹与去重机制说明（想了解 Phase 0/6 细节时读）。

## 脚本清单

- `scripts/ci_bootstrap.py` —— 初始化 / 读取 `.ci`，输出当前状态（是否已建图、已创建哪些 issue）。
- `scripts/check_graph.py` —— 判断 GitNexus 图谱是否需要重建（`--mark` 在建图后写标记）。
- `scripts/fingerprint.py` —— 计算 issue 指纹并做本地去重检查（`--title/--body-file --check`）。
- `scripts/create_issue.py` —— 官方 API 建单（支持 `--dry-run`），成功后自动压缩记录到 `.ci`。
- `scripts/_cihelpers.py` —— 上述脚本共享的工具函数（路径、仓库识别、指纹、记录读写），一般不单独调用。
