---
name: repo-issue-hunter
description: 分析一个已有代码仓库，从 Bug Fix 和 Feature 两个方向挖出最值得做的问题、规范成标准 issue，经用户确认后用官方 API 建单，靠 .ci 文件夹压缩记录去重。开工前先做前置工具校验（git/python3 必需，node/gh 可选）和参数解析：`--repo` 指定目标仓库、`--direction` 指定要核实的具体问题方向（给了就只定向核实、不再全仓扫描）、`--skip` 跳过除鉴权外的所有确认点，全程按 Phase 输出 `[第几步/共7步]` 进度提示。当用户说"帮这个项目提 issue / 找 bug / 提需求 / 自动建 issue / 扫一遍仓库开工单"，或希望系统性地把改进点落成 GitHub issue 时应主动触发；用户直接描述具体问题（如"登录模块可能有并发 bug"）时，就带上 `--direction` 定向核实而不是全仓扫描。与 repo-product-analyst 互补：那个出分析报告，这个出可执行的 issue。Use this to scan a repo for bugs/feature gaps and file them as GitHub issues via the official API, with .ci-based dedup.
---

# Repo Issue Hunter（仓库 → 标准 issue → 官方 API 建单，带 .ci 去重）

把一个**已存在的代码仓库**扫一遍，从 **Bug Fix** 和 **Feature** 两个方向找出最值得做的事，规范成标准 issue，经用户确认后用 **GitHub 官方 API** 创建，并把结果**压缩记录到 `.ci` 文件夹**，保证下次执行不会重复建单。

**贯穿始终的四条原则：**
- **`.ci` 先行**：Skill 一被触发，第一件事就是读当前仓库的 `.ci` 文件夹，拿到"已经建过哪些 issue / 是否已建过图谱"，后续所有判断都建立在这个已知状态之上。
- **证据优先**：每个 Bug / Feature 结论都尽量挂上具体代码证据（文件 / 模块 / 函数 / 入口）。说不清来源的不写。
- **幂等与安全（除鉴权外均可被 `--skip` 跳过）**：本地验证代码必须幂等、绝不造成数据丢失或污染；任何涉及模型调用 / 有计费的测试，跑之前先向用户确认；建 issue 前必须经用户明确同意。用户若在调用时传了 `--skip`，这些确认点都直接跳过、按计划执行——**唯一例外是 Phase 5 的建单鉴权**（`gh` 登录或 `GITHUB_TOKEN`）：没有鉴权就是没法调 API，这不是"审批"，是硬性技术前提，`--skip` 影响不到它。细节见 Phase 0.1。
- **语言跟随用户**：issue 正文与对话默认用用户当前语言（中文用户输出中文）。

---

## 进度提示：贯穿全程的可观测性

每次**切换到一个新的子步骤**时，先输出一行进度标识，再做那件事，格式固定为：

```
[第 X/7 步] Phase <N> · <这一小步具体在干什么，一句话>
```

- **X/7** 对应 Phase 0 → Phase 6 共 7 个顶层阶段，一一对应（Phase 0 → `1/7`……Phase 6 → `7/7`）。
- Phase 0 内部有子步骤（参数解析/工具校验/定位仓库/.ci）、Phase 2 内部有两条轨道（Bug/Feature）时，在同一行追加子步骤名，如 `[1/7] Phase 0 · 校验前置工具（git/python3/node/gh）`、`[3/7] Phase 2 · 轨道 A Bug Fix 分析`；带了 `--direction` 时改成 `[3/7] Phase 2 · 定向核实方向 2/3「登录并发问题」`，带上第几个方向/共几个、以及方向的简短描述。
- **粒度**：每进入一个子阶段报一次即可，不用每条命令都报；正常的命令输出、分析过程照常展示，进度行只是加在前面的一行"路标"。
- 这只是给已有的 Phase 0～6 加一行状态提示，**不改变**任何判断逻辑或执行顺序。

---

## 总体流程

严格按 Phase 0 → Phase 6 顺序执行。脚本都在 `scripts/`，从**仓库根目录**运行（`python3 <skill>/scripts/xxx.py ...`）。

### Phase 0 — 前置条件校验 & 命令行参数解析 & 加载 `.ci`（启动引导，必做）

1. **解析命令行参数**：用户调用本 Skill 时，除了自然语言描述，也可能带类似命令行的参数：
   - **`--repo <owner/repo 或完整 URL>`**：指定目标仓库。本地已有对应 clone 就直接 `cd` 进去；本地没有 → 先 `cd` 到合适的父目录 `gh repo clone owner/repo`（或 `git clone`）再 `cd` 进去（**clone 前向用户确认一次，除非带了 `--skip`**）。不给就默认用当前目录所在仓库。
   - **`--direction "<问题/方向描述>"`**：指定要核实的具体方向，而不是让 Skill 自己满仓库扫。用户已经知道大概是什么问题（例如"登录模块在并发下可能有竞态""想给导出功能加个批量模式"），就直接把描述传进来。可重复传多次（每次一个方向），或在一次里用分号 `;` / 换行分隔多个方向。识别到 `--direction` 后，**Phase 2 切换成"定向核实模式"**：只针对给出的这几个方向去挂证据、判断是不是真问题/真需求，**不再对整个仓库做开放式扫描去找别的候选**——细节见 Phase 2 开头的分支说明。
   - **`--skip`**：跳过**除 Phase 5 建单鉴权以外**的所有确认点，直接执行。具体覆盖：GitNexus MCP 配置写入确认（Phase 1，若走到这一步）、涉及模型调用/外部计费的本地验证确认（Phase 2 轨道 A）、Phase 5 建单前的空跑展示 + 等待用户"可以创建"的确认。`gh` 登录或 `GITHUB_TOKEN` 这类鉴权前提**不受影响**——没鉴权就是没法调用 API，这一步没有跳过的选项。
   - 三个参数都**可选**，可以任意组合或都不传。都没传 → 默认当前目录仓库、Phase 2 走全仓开放式扫描、所有确认点正常等待用户回应。
   - 把解析出的值记下来，后面 Phase 0.3、Phase 1、Phase 2、Phase 5 直接用，不用重复问。

2. **前置工具存在性检查**（新会话/新环境先做一次）：本 Skill 依赖 `git`、`python3` 两个**必需**工具（`python3` 用来跑 `scripts/` 下所有脚本），以及 `node`（GitNexus 用）、`gh`（建单鉴权用，缺失可用 `GITHUB_TOKEN` 兜底）两个**可选**工具。逐一探测：
   ```bash
   command -v git     >/dev/null 2>&1 && echo "git     OK: $(git --version)"         || echo "git     MISSING（必需）"
   command -v python3 >/dev/null 2>&1 && echo "python3 OK: $(python3 --version)"      || echo "python3 MISSING（必需）"
   command -v node    >/dev/null 2>&1 && echo "node    OK: $(node --version)"         || echo "node    MISSING（可选，GitNexus 用）"
   command -v gh      >/dev/null 2>&1 && echo "gh      OK: $(gh --version | head -1)" || echo "gh      MISSING（可选，可用 GITHUB_TOKEN 兜底）"
   ```
   - **`git` 或 `python3` 缺失**（必需）→ Skill 无法运行。按 **[references/setup-git-python.md](references/setup-git-python.md)** 对应操作系统的章节安装（安装命令通常需要 `sudo`/管理员权限，属于会留下持久改动的操作，**动手前先把命令展示给用户、拿到明确同意再执行，除非带了 `--skip`**）；装完重新探测一遍，确认可用再继续。环境完全无法安装 → 如实告知后停止。
   - **`node` 缺失**（可选）→ 不阻塞，Phase 1 会走手动定位的降级方案；想用 GitNexus 加速可参照 `references/setup-gitnexus.md` 安装。
   - **`gh` 缺失**（可选）→ 不阻塞，Phase 5 会自动改用 `GITHUB_TOKEN` 兜底鉴权；两者都没有时再按 `references/setup-gh.md` 处理。

3. 定位仓库根目录：`git rev-parse --show-toplevel`。所有后续命令都 `cd` 到这里（Phase 0.1 已处理 `--repo` 指向的仓库不在本地的情况）。
4. 运行引导脚本，初始化并读取 `.ci`：
   ```bash
   python3 <skill>/scripts/ci_bootstrap.py
   ```
   它会（不存在则创建、已存在则只读）输出一份 JSON 状态：`.ci` 是否就绪、图谱是否已建、**已创建过哪些 issue（类型 / 标题 / 编号 / URL）**。
5. 把"已创建 issue 列表"记在脑子里——**它是本轮去重的基线**。后面任何候选 issue 都要先和它比对，重复的直接丢弃。
   > `.ci/` 是在用户自己仓库里建的本地文件夹，属常规本地写入，无需额外确认；但"建 issue、改全局配置"等副作用操作仍要确认（除非 `--skip`）。`.ci` 的结构与去重机制见 `references/ci-folder.md`。

### Phase 1 — 建立 / 复用知识图谱（GitNexus）

先建图谱、再做分析：直接读全部源码又慢又烧 Token，先用 GitNexus 把代码库索引成知识图谱，之后用图谱查询精准定位，只读真正需要的部分。

1. 判断是否需要重新建图（避免重复建图）：
   ```bash
   python3 <skill>/scripts/check_graph.py
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
     python3 <skill>/scripts/check_graph.py --mark
     ```
3. 探索优先用 GitNexus MCP 工具（成本远低于逐文件读）：`query "<概念>"` 定位代码簇、`context <符号>` 看 360° 视图、`impact <符号>` 看影响面、`cypher "<图查询>"` 挖架构关系。
   > **降级方案**（GitNexus 跑不起来 / 离线 / 缺 node）：不要卡死。改为手动探索——读 README、列目录树、看包管理清单、定位入口与核心模块、抽样读关键代码。后续 Phase 照常，只是证据来自人工阅读。

### Phase 2 — 双轨分析：Bug Fix 与 Feature

围绕图谱产出候选，分两种模式，取决于 Phase 0.1 是否解析到 `--direction`：

- **默认：全仓开放式扫描**（没有 `--direction`）——按下面轨道 A / 轨道 B 的方法论，自主在整个仓库范围内找候选。
- **`--direction` 给了方向：定向核实模式**——用户已经把要查的问题/需求描述给你了，**候选就是这几条，不用再对仓库做开放式扫描去找别的**。这时 Phase 2 的工作变成：
  1. 逐条方向，先判断它更像 Bug 还是 Feature（描述"哪里坏了/不对"→走轨道 A 的证据与验证方法；描述"想要什么能力"→走轨道 B 的两问），套用对应轨道下面的方法论和红线（本地验证的幂等/安全/计费确认、Feature 的"为什么+实现可能性"）。
  2. 用 GitNexus 图谱（`query`/`context`/`impact`）**精准定位这条方向对应的代码**，把"现象/触发条件/期望 vs 实际/根因"或"为什么需要+实现可能性"坐实、挂上具体证据——这是核实，不是重新调研整个仓库有没有别的问题。
  3. 如果某条方向核实下来发现根本不成立（代码里其实没这个问题，或已经支持了），**如实告诉用户这条方向查证后不成立**，别为了凑数硬造证据，也别因为用户提了就直接采信。
  4. 定向模式下**不额外补充**用户没提到的候选——即使分析过程中顺带发现了别的疑点，也只在结尾提一句"顺带发现了 xxx，如果需要下次可以专门查"，不要自作主张塞进本轮的建单清单。
  - **每条都要挂代码证据**，这一条无论哪种模式都不能省。

#### 轨道 A：Bug Fix（修 Bug）
用图谱定位可疑点：缺失/错误的异常处理、边界与空值、并发与竞态、资源泄漏、契约不一致（接口与实现/文档不符）、错误的默认值、明显的逻辑漏洞等。

**本地验证的授权与红线**——允许写“类似单测”的代码在本地跑来确认 bug，但必须遵守：
- **严格幂等**：同一段验证代码反复跑，结果一致、不留副作用。
- **绝不破坏数据**：禁止运行任何会写生产数据、删除文件、改动外部状态（真实数据库/线上服务/用户文件）的测试。一律用临时目录、内存态、fixture 或 mock。
- **付费 / 模型调用要先确认（`--skip` 时也跳过，但仍要展示进度提示）**：任何会触发真实模型调用、外部 API 计费、或产生消费的验证，**跑之前先明确告诉用户成本并征得同意**，不要擅自执行；用户若传了 `--skip` 则直接跑，不等待回应。
- 拿不准某个验证是否安全 → **默认不跑**。这条和上面"先确认"不是一回事：上面是"知道要花钱/调模型，等用户点头"，`--skip` 省的是这个点头动作；这条是"根本没判断出安全与否"，没有明确方案可执行，`--skip` 不会把"不确定"变成"确定安全"，该不跑还是不跑，跳过验证、如实告知用户，继续下一条分析。

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

### Phase 5 — 用官方 API 创建 issue（**需用户明确确认，除非 `--skip`**）

创建 issue = 在（可能公开的）仓库里发布内容，属于不可轻易撤销的副作用操作，**必须先经用户同意**——这一等待可以被 `--skip` 免除，但**建单鉴权本身不能被免除**：没有 `gh` 登录或 `GITHUB_TOKEN`，Phase 5 就是跑不下去，这不是审批，是硬性技术前提。

0. **确认鉴权可用**（`gh` 登录或 `GITHUB_TOKEN`，二选一即可）：
   ```bash
   gh auth status   # 装了 gh 的话先看这个；没装就直接检查 GITHUB_TOKEN/GH_TOKEN 环境变量
   ```
   - 两者都没有 → 明确告诉用户要跑哪条命令，不要代替用户登录或索取 token：
     > 请在终端运行 `gh auth login`，按提示用浏览器完成授权；或者 `export GITHUB_TOKEN=ghp_xxx` 设置一个有 issues 写权限的 token，用哪种都行。完成后不用回来告诉我，我会自动检测到。
   - 说完之后**不要傻等**，转为后台轮询：大约每 10 秒检查一次，检测到 `gh auth status` 成功**或** `GITHUB_TOKEN`/`GH_TOKEN` 环境变量出现即结束轮询：
     ```bash
     until gh auth status >/dev/null 2>&1 || [ -n "$GITHUB_TOKEN$GH_TOKEN" ]; do sleep 10; done; echo "鉴权已就绪"
     ```
     用 `run_in_background` 起这个 until 循环（或用 Monitor 工具挂起等待），循环退出即代表鉴权就绪，会收到完成通知。轮询超过约 5 分钟仍未就绪 → 停止轮询，回来问用户卡在哪，详细方案见 `references/setup-gh.md`。
   - 已就绪 → 继续下一步。
1. **先空跑**，把最终清单和去重结果摆给用户看（这一步始终执行，不受 `--skip` 影响，因为它本身不是"等确认"，是"准备材料"）：
   ```bash
   python3 <skill>/scripts/create_issue.py --dry-run \
     --type bug --title "…" --body-file /tmp/issue1.md
   ```
   `--dry-run` 会做完本地 + 远端去重检查、打印将要创建什么，但**不调用 API、不写记录**。对每个候选都空跑一遍，然后把"将创建 N 条 issue：标题列表 + 正文预览 + 去重结论"呈现给用户。
2. **等用户明确说"可以创建 / 确认"后**（若带了 `--skip`，跳过等待、直接进行下一步，但空跑结果仍要展示过），再逐条真正创建（去掉 `--dry-run`）：
   ```bash
   python3 <skill>/scripts/create_issue.py \
     --type bug --title "…" --body-file /tmp/issue1.md
   ```
   鉴权见 `references/github-api.md`：优先用已登录的 `gh` CLI，否则用环境变量 `GITHUB_TOKEN`（需要 issues 写权限）。仓库默认从 `git remote origin` 自动识别，也可 `--repo owner/name` 显式指定（若 Phase 0.1 解析到 Skill 级的 `--repo`，这里保持一致，一般不用再传）。
3. 若鉴权实在配不上（Phase 5.0 轮询超时后用户仍未解决），**不要创建**，把 issue 内容直接给用户，让他自己建，并说明缺什么（`gh` 登录 / `GITHUB_TOKEN`，指向 `references/setup-gh.md`）。

### Phase 6 — 压缩记录到 `.ci`（自动，保证幂等）

`create_issue.py` 创建成功后会**自动**把这条 issue 压缩成一条指纹记录（`fingerprint + 类型 + 标题 + 编号 + URL + 时间`），追加到 `.ci/issues/created.jsonl`（可加 `--gzip` 额外产出 `.gz` 压缩快照）。

这带来天然幂等：下次再跑本 Skill，Phase 0 读到这些记录、Phase 3/Phase 5 的去重就会自动跳过已建的 issue，不会重复创建。**不要手动改 `.ci/issues/` 里的记录文件**——它是去重的真相来源。

---

## 结束前的自检清单

- [ ] Phase 0 做了工具存在性检查（git/python3 必需）、解析了 `--repo`/`--skip`，真的读了 `.ci`，拿到了已创建 issue 基线？
- [ ] 图谱是复用还是新建，判断依据是 `check_graph.py` 而不是拍脑袋？
- [ ] 每个 Bug/Feature 都挂了代码证据？本地验证守住了幂等 + 不破坏数据；付费/模型调用的确认按 `--skip` 决定是否等待，但"不确定安全就不跑"这条无论如何都生效？
- [ ] 若带了 `--direction`：Phase 2 只核实了给出的那几条方向，没有顺手对全仓做开放式扫描去找别的候选？查证不成立的方向如实告知了，没有硬凑？
- [ ] 反思收敛到 ≤5 个，且和 `.ci` 已建列表去重过？
- [ ] 格式严格套了 `references/issue-formats.md` 的模板？
- [ ] 建单前鉴权（`gh`/`GITHUB_TOKEN`）真的就绪了、**空跑**做了，且用户确认（或 `--skip`）都处理了？
- [ ] 建成功的 issue 都进了 `.ci`？（`create_issue.py` 会自动做，确认没报错即可）
- [ ] 全程按 `[X/7]` 输出了进度提示，没有跳步、没有一次性哑巴执行到底？

---

## 参考文件（按需读取）

- `references/issue-formats.md` —— Bug Fix / Feature 的完整格式模板与示例（Phase 4 必读）。
- `references/github-api.md` —— `gh` CLI 与 GitHub REST API 建单的鉴权、用法、去重与错误处理（Phase 5 必读）。
- `references/setup-git-python.md` —— `git` / `python3` 安装（Phase 0 发现二者缺失时读，跨平台）。
- `references/setup-gh.md` —— `gh` 安装与鉴权配置（当 `gh` 未装/未登录且无 `GITHUB_TOKEN` 时读）。
- `references/setup-gitnexus.md` —— GitNexus 安装与配置（当 `gitnexus`/`npx` 缺失或建图失败时读，含降级方案）。
- `references/ci-folder.md` —— `.ci` 文件夹结构、指纹与去重机制说明（想了解 Phase 0/6 细节时读）。

## 脚本清单

- `scripts/ci_bootstrap.py` —— 初始化 / 读取 `.ci`，输出当前状态（是否已建图、已创建哪些 issue）。
- `scripts/check_graph.py` —— 判断 GitNexus 图谱是否需要重建（`--mark` 在建图后写标记）。
- `scripts/fingerprint.py` —— 计算 issue 指纹并做本地去重检查（`--title/--body-file --check`）。
- `scripts/create_issue.py` —— 官方 API 建单（支持 `--dry-run`），成功后自动压缩记录到 `.ci`。
- `scripts/_cihelpers.py` —— 上述脚本共享的工具函数（路径、仓库识别、指纹、记录读写），一般不单独调用。
