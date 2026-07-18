---
name: github-issue-solver
description: 自动分诊并批量修复 GitHub 仓库的 Open Issue（默认每批 3 个、上限 5）：逐个理解 issue → 定位代码（优先 GitNexus）→ 建 ai-feat- linked branch → 修改并写测试，全过后打 AISolved 标签、写方案评论请 owner review；不开 PR、不关闭 issue，全程只用 gh CLI、未登录会引导登录。支持 `--repo`/`--issue`/`--skip` 参数、前置工具自检（git/gh/node/jq）和分步进度提示。当用户说"处理这个仓库的 issue""解决几个 issue""自动修一批 bug""处理 issue #12 #15"等，或给出仓库希望自动分诊修复时应主动触发。Use for automated GitHub issue triage-and-fix workflows.
---

# GitHub Issue Solver（自动分诊 + 修复 Open Issue）

把一个仓库的 Open Issue 变成"已修复、有分支、有测试、待人工 review"的状态。核心是一条可重复的流水线：**筛选 → 逐个修 → 收尾（远程写操作前先确认）**。

**四条贯穿始终的原则：**
- **只用 `gh`，绝不碰密钥**：所有 GitHub 操作走 `gh` CLI（它复用用户已登录的凭证）。永远不要读取、写入或要求用户粘贴 token / 密码 / API key。未登录就引导登录，绝不代替用户输入凭证——**这一条不受 `--skip` 影响，gh 登录永远要走正常检查/等待流程**。
- **不开 PR，只做到分支**：本 Skill **不发起 PR**。职责边界是"把 issue 在一个绑定好的分支上改完、测好、推上去"，是否开 PR / 合并由人来决定。
- **远程写操作前先确认（除非 `--skip`）**：push、创建 linked branch、评论、改 label / assignee 都是对仓库可见的写操作。本地准备好（分支、提交、测试通过）之后、真正动远程之前，把"将要做什么"汇总给用户，拿到明确同意再执行（见 Step 3）。用户若在调用时传了 `--skip`，则跳过这一步和其余所有确认点，直接执行——细节见 Step 0.1。
- **验证通过才收尾打标**：`AISolved` 标签和方案评论**放到最后**——只有分支已可靠绑定、测试通过、代码已推上去、收尾自检全过之后才打标 + 评论。修不动或没把握就如实说明、保留分支交人工，不假装解决了。**任何情况下都不由 AI 关闭 issue**（关不关由 owner 决定）。

---

## 进度提示：贯穿全程的可观测性

每次**切换到一个新的子步骤**时，先输出一行进度标识，再做那件事，格式固定为：

```
[第 X/4 步] Step <N> · <这一小步具体在干什么，一句话>
```

- **X/4** 对应文档四个顶层 Step：Step 0 → `1/4`，Step 1 → `2/4`，Step 2（含收尾 Step 3）→ `3/4` 和 `4/4`。
- Step 0 / Step 2 内部有子步骤时，在同一行追加子步骤名；Step 2 是**逐 issue 循环**，要带上"处理到第几个 issue"：
  | 阶段 | 示例 |
  |---|---|
  | Step 0.1 解析参数 | `[1/4] Step 0 · 解析命令行参数（--repo/--issue/--skip）` |
  | Step 0.2 工具校验 | `[1/4] Step 0 · 校验前置工具（git/gh/node/jq）` |
  | Step 0.3 gh 登录 | `[1/4] Step 0 · 检查/等待 gh 登录` |
  | Step 0.4 定位仓库 | `[1/4] Step 0 · 定位目标仓库` |
  | Step 1 | `[2/4] Step 1 · 拉取并筛选 Open Issues（共 <M> 个候选）` |
  | Step 2a | `[3/4] Step 2 · issue 2/3（#15）· 2a 理解 issue` |
  | Step 2b～2e | 同上前缀，把 `2a` 换成 `2b 定位代码` / `2c 创建 linked branch` / `2d 修改代码` / `2e 写测试并验证` |
  | Step 3 | `[4/4] Step 3 · issue 2/3（#15）· 收尾（push/assign/打标/评论）` |
  | 全部完成 | `[4/4] Step 3 · 全部处理完成，生成小结` |
- **粒度**：每进入一个子步骤报一次即可，不用每条 bash 命令都报；正常的命令输出、解释文字照常展示，进度行只是加在前面的一行"路标"，不用为了控制篇幅而省略必要信息。
- 这只是给已有的 Step 0～3 / 2a～2e 加一行状态提示，**不改变**任何判断逻辑或执行顺序。

---

## Step 0 — 前置条件校验 & 命令行参数解析（参数 → 工具 → 登录 → 定位仓库）

1. **解析命令行参数**：用户调用本 Skill 时，除了自然语言描述，也可能带类似命令行的参数，优先识别并按参数走，不用再靠猜自然语言：
   - **`--repo <owner/repo 或完整 URL>`**：指定目标仓库。例如 `--repo octocat/hello-world`、`--repo https://github.com/octocat/hello-world`。识别到后直接作为 Step 0.4「定位目标仓库」的输入，等价于"用户给了仓库"。
   - **`--issue <编号[,编号...]>`**：指定要处理的一批 issue 编号。逗号分隔、空格分隔、带不带 `#` 前缀都要能识别，例如 `--issue 12,15,20`、`--issue #12 #15`。识别到后直接作为 Step 1.3「确定数量」的输入，等价于"用户指定了编号"。
   - **`--skip`**：跳过**除 gh 登录以外**的所有审批/确认点，直接执行。具体覆盖：
     - Step 0.2 缺失必需工具（git/gh）时的安装前确认；
     - Step 0.4 `--repo`/自然语言指定的仓库本地没有时的 clone 前确认；
     - Step 1.4 选中 issue 列表的启动确认；
     - Step 3 收尾时的远程写操作（push/assign/打标/评论）批量确认。
     `--skip` **不影响** Step 0.3 的 gh 登录检查——没登录一样要引导用户 `gh auth login` 并轮询等待，这一步没有跳过的选项，因为跳过了就没法执行任何 GitHub 写操作。传了 `--skip` 后这些原本需要用户点头的地方改为直接执行，但**进度提示照常一步不落地展示**（见上方"进度提示"约定），让用户能追踪到底做了什么，只是不用逐一等待确认。
   - 三个参数都是**可选**的，互不依赖，可以任意组合或都不传。都没传 → 按原有规则走（自然语言里找、找不到就用默认值：当前目录仓库、编号最小的 N=3 个、逐项确认）。
   - **`--repo`/`--issue` 只负责"选哪个仓库、选哪些 issue"，不改变其余任何规则**：`--issue` 传入的编号照样要过 assignees 非空跳过、已带 `AISolved` 跳过的检查；总数仍然**上限 5 个**，超出只取前 5 并提醒用户。
   - 把解析出的值（含是否带 `--skip`）记下来，后面 Step 0.2、0.4、1.3、1.4、Step 3 直接用，不用再重复问用户一遍。

2. **工具存在性检查**（新会话/新环境先做一次）：本 Skill 依赖 `git`、`gh` 两个**必需**工具，以及 `node`（GitNexus 加速用）、`jq`（排序小抓手用）两个**可选**工具。逐一探测：
   ```bash
   command -v git  >/dev/null 2>&1 && echo "git  OK: $(git --version)"         || echo "git  MISSING（必需）"
   command -v gh   >/dev/null 2>&1 && echo "gh   OK: $(gh --version | head -1)" || echo "gh   MISSING（必需）"
   command -v node >/dev/null 2>&1 && echo "node OK: $(node --version)"        || echo "node MISSING（可选，用于 GitNexus 加速定位）"
   command -v jq   >/dev/null 2>&1 && echo "jq   OK: $(jq --version)"          || echo "jq   MISSING（可选，用于 Step 1 排序小抓手）"
   ```
   - **`git` 或 `gh` 缺失**（必需）→ Skill 无法运行。查阅同目录的 **[INSTALL.md](./INSTALL.md)**，按用户操作系统（macOS / Linux / Windows）执行对应章节的安装命令。安装命令通常需要 `sudo` / 管理员权限、会改动系统包管理器状态，**属于会留下持久改动的操作，动手前先把具体命令展示给用户、拿到明确同意再执行**（若 Step 0.1 解析到 `--skip`，跳过确认、直接安装，但进度提示要照常展示"正在安装 xxx"）；装完重新跑一遍上面的探测命令，确认真的可用了再继续。若用户环境完全无法安装（沙箱/离线/无权限），如实告知具体缺什么、为什么必需，然后停止，不要假装能绕过继续。
   - **`node` 缺失**（可选）→ 不阻塞，告知用户 GitNexus 加速定位不可用，Step 2b 会直接走手动定位的降级方案。用户如果想要更快的定位能力，可参照 `INSTALL.md` 的 node 章节安装，同样先确认再执行。
   - **`jq` 缺失**（可选）→ 不阻塞，Step 1 的排序小抓手改成肉眼筛选 `gh issue list` 的 JSON 输出即可。

3. **确认 `gh` 已登录，未登录则引导 + 轮询等待**：
   ```bash
   gh auth status
   ```
   - **已登录** → 直接继续下一步。
   - **未登录**（命令报错 / 提示 not logged in）→ **不要**自己去找 token、也不要代替用户输入任何凭证或替用户跑登录命令。`gh auth login` 是交互式、需要打开浏览器授权的流程，必须由用户在自己的终端里执行，明确告诉用户要跑哪条命令：
     > 请在终端运行 `gh auth login`，按提示选择 GitHub.com → HTTPS/SSH → 用浏览器完成授权。完成后不用回来告诉我，我会自动检测到。
   - 说完之后**不要傻等或反复手动追问**，改为后台轮询：大约每 10 秒检查一次登录状态，检测到成功即结束轮询，不需要用户手动确认：
     ```bash
     until gh auth status >/dev/null 2>&1; do sleep 10; done; echo "gh 已登录"
     ```
     用 `run_in_background` 起这个 until 循环（或用 Monitor 工具挂起等待），循环自然退出就代表登录成功，会收到完成通知，无需再逐次调用 `gh auth status` 打扰用户。
   - **超时兜底**：轮询超过约 5 分钟（≈30 次探测）仍未登录成功，停止轮询，主动回来问用户卡在哪一步（例如浏览器授权页没跳转、网络受限）。纯 SSH / 无桌面环境等场景，参考 `INSTALL.md` 中 gh 章节的报错处理（如改用 "Paste an authentication token" 方式，仍由用户自己在浏览器生成并粘贴，Skill 不代为操作）。
   - 已登录 → 继续 Step 0 的下一步。

4. **定位目标仓库**：
   - Step 0.1 解析到 **`--repo`** → 用它指定的仓库；本地没有的话，先 `cd` 到合适的父目录，`gh repo clone owner/repo` 再 `cd` 进去（**clone 前向用户确认一次**，属于会在磁盘上落东西的操作；若带 `--skip` 则跳过确认直接 clone）。
   - 没有 `--repo`、但自然语言里**给了仓库**（`owner/repo` 或 URL）且本地没有 → 同上，clone 前确认一次（同样受 `--skip` 影响）。
   - 都没指定 → 默认当前目录所在仓库。确认它有 GitHub remote：`gh repo view --json nameWithOwner -q .nameWithOwner`。
   - 后续所有 `gh` 命令若不在仓库目录内，统一带 `-R owner/repo`。

5. **记下仓库 owner**（收尾请 review、@ 提及时要用）：
   ```bash
   gh repo view --json owner,defaultBranchRef -q '.owner.login, .defaultBranchRef.name'
   ```

---

## Step 1 — 拉取并筛选 Open Issues

目标：选出**本批要处理的 issue 列表**。

1. 拉取全部 Open Issue（`gh issue list` 默认已排除 PR）：
   ```bash
   gh issue list --state open --limit 200 \
     --json number,title,assignees,labels,url
   ```

2. **按规则筛选与排序**：
   - **升序**：按 `number` 从小到大排（先处理最早/编号最小的）。
   - **跳过已分配**：`assignees` 数组非空的一律跳过（说明已经有人认领）。
   - **跳过已解决**：已带 `AISolved` 标签的跳过。

3. **确定数量**：
   - Step 0.1 解析到 **`--issue`** → 就用这些编号；仍要逐个检查 assignees，若某个已被分配，**默认跳过并告知用户**（除非用户明确要求照做）；同样检查是否已带 `AISolved` 标签。指定超过 5 个时提醒并只取前 5 个。
   - **`--issue` 指定的编号如果在 Step 1.1 拉到的 Open Issue 列表里根本找不到**（可能已关闭、编号不存在、或本来就是 PR 不是 issue）→ **弹一条警告**告知用户具体是哪个编号、大致原因（能查到就带上，如 `gh issue view <num> --json state,title` 看到 `CLOSED` 就写"已关闭"；命令报 404 就写"编号不存在"），然后**跳过这个编号、正常往下走**，继续处理其余指定的编号，不中断整个流程。
   - 没有 `--issue`、但用户**在自然语言里指定了编号**（如"处理 #12 #15 #20"）→ 同上两条规则（跳过已分配/已解决要告知、找不到也要警告后跳过）一并处理。
   - 都没指定 → 从筛选后的列表里取编号最小的 **N** 个，默认 **N=3**，**上限 5**。

4. **把选中的 issue 列给用户确认**（编号 + 标题 + 链接），得到"开始"再进入 Step 2；若 Step 0.1 解析到 `--skip`，跳过这个确认，展示完列表直接进入 Step 2。这一步很轻，但能避免选错仓库/选错 issue 白干一场，所以即使 `--skip` 也要把列表**展示出来**，只是不用等"开始"这个回复。

> 排序小抓手（可用 jq 过滤 + 排序）：
> ```bash
> gh issue list --state open --limit 200 \
>   --json number,title,assignees,labels \
>   | jq 'map(select((.assignees|length)==0)
>         and (all(.labels[].name; .!="AISolved")))
>       | sort_by(.number)'
> ```

---

## Step 2 — 逐个 issue 解决（对选中的每个 issue 循环执行）

### 2a. 理解 issue
```bash
gh issue view <num> --json number,title,body,labels,comments
```
读懂：到底是什么问题 / 复现条件 / 期望行为。看一眼已有评论，避免重复别人已经指出的方向。

### 2b. 定位相关代码（优先用 GitNexus 加速）
直接 `cat` 整个目录既慢又烧 Token。优先用 **GitNexus** 把仓库索引成知识图谱、再精准定位：
```bash
npx gitnexus analyze     # 首次/大改动后建/刷新索引；中型项目通常一分钟内
gitnexus status          # 确认索引成功
```
若 GitNexus MCP 可用，用 `query "<issue 关键词/功能>"` 找相关代码簇、`context <符号>` 看某函数的调用方/被调用方、`impact <符号>` 判断改动影响面。

> **降级方案**（缺 node / 装不上 / 离线）：不要卡死。改为手动定位——读 README/docs、grep 关键字、看目录树与入口文件、抽样阅读相关模块。后续步骤照常。

### 2c. 创建 linked branch（绑定到 issue）并本地检出

命名规则固定为 **`ai-feat-<简短英文描述>-<编号>`**——**用连字符，不带斜杠 `/`**。带斜杠的分支名会让部分 `gh` / GraphQL 调用报错，所以一律用 `ai-feat-` 前缀。
- 英文描述取 2–4 个词的 kebab-case，概括问题（issue 是中文就翻成英文）。
- **示例**：#42「登录点击后崩溃」→ `ai-feat-fix-login-crash-42`；#7「列表分页参数越界」→ `ai-feat-paginate-oob-7`。

**用 GitHub 的 linked branch 机制来绑定分支和 issue**（不开 PR 时，这是把二者可靠关联起来的正规方式）。做法是"远程先建、且在建的同时就绑定"，再检出到本地——这样绑定在创建那一刻就成立，不依赖后续 PR。严格按下方《Linked branch 绑定 + 验证》小节的 3 步执行：**拿 ID → 创建 linked branch → 验证绑定**。

创建成功后检出到本地开工：
```bash
git fetch origin
git checkout -b ai-feat-fix-login-crash-42 origin/ai-feat-fix-login-crash-42
```
> 若分支已存在（重跑场景），直接 `git checkout ai-feat-fix-login-crash-42` 继续，不必重复创建。

### 2d. 分阶段修改 + 有信息量的提交
允许拆成多次提交，边改边 commit，让每条 commit message 讲清这一步做了什么。推荐 Conventional Commits 并带上 issue 号：
```
fix(auth): guard null token before redirect (#42)
test(auth): cover empty-session login path (#42)
```

### 2e. 写并运行测试验证
补一个能覆盖该 bug 的测试，然后按项目技术栈跑测试，确认修复有效且没引入回归：
- Python → `pytest`（或项目自定义命令）
- Go → `go test ./...`
- Rust → `cargo test`
- Node → `npm test` / `pnpm test`
先探测项目实际的测试命令（看 Makefile / package.json scripts / pyproject 等）再跑。

**测试通过** → 进入 Step 3 收尾。
**测试跑不通 / 修不动** → 不收尾、不打 AISolved。如实向用户说明卡在哪，保留分支交人工，继续下一个 issue。

---

## Linked branch 绑定 + 验证（怎么做）

不开 PR 时，把分支和 issue 可靠关联起来靠 GitHub 的 **linked branch**（issue 详情页 "Development" 区显示的关联分支）。它通过 GraphQL 的 `createLinkedBranch` 变更建立——**该变更会在远程创建这个分支并同时绑定到 issue**，所以采用"远程先建、当场绑定、再检出本地"的顺序最可靠，不依赖 PR。全部走 `gh api graphql`，仍复用已登录凭证、不碰密钥。

**第 1 步：拿到需要的 ID。** issue 的 node id、仓库 id、默认分支及其 HEAD commit（作为新分支的基点）：
```bash
ISSUE_ID=$(gh issue view <num> --json id -q .id)

# 一次性取回：仓库 id / 默认分支名 / 默认分支 HEAD 的 oid
read REPO_ID BASE_BRANCH BASE_OID < <(gh api graphql -f query='
  query($owner:String!,$name:String!){
    repository(owner:$owner,name:$name){
      id
      defaultBranchRef{ name target{ oid } }
    }
  }' -f owner=<owner> -f name=<repo> \
  --jq '.data.repository | "\(.id) \(.defaultBranchRef.name) \(.defaultBranchRef.target.oid)"')
```

**第 2 步：创建 linked branch（建分支 + 绑定 issue，一步到位）。** 分支名用不带斜杠的 `ai-feat-<desc>-<编号>`：
```bash
gh api graphql -f query='
  mutation($issueId:ID!,$repoId:ID!,$oid:GitObjectID!,$name:String!){
    createLinkedBranch(input:{issueId:$issueId, repositoryId:$repoId, oid:$oid, name:$name}){
      linkedBranch{ id ref{ name } }
    }
  }' -f issueId="$ISSUE_ID" -f repoId="$REPO_ID" -f oid="$BASE_OID" \
     -f name="ai-feat-fix-login-crash-42"
```

**第 3 步：验证绑定确实成立（必须做，不能想当然）。** 直接查这个 issue 的 `linkedBranches`，确认分支名出现在结果里：
```bash
gh api graphql -f query='
  query($owner:String!,$name:String!,$num:Int!){
    repository(owner:$owner,name:$name){
      issue(number:$num){ linkedBranches(first:20){ nodes{ ref{ name } } } }
    }
  }' -f owner=<owner> -f name=<repo> -F num=<num> \
  --jq '.data.repository.issue.linkedBranches.nodes[].ref.name'
```
- 输出里**包含** `ai-feat-fix-login-crash-42` → 绑定成功，继续检出本地开工（回到 Step 2c 的 `git checkout` 命令）。
- 输出里**没有** → 绑定失败，别往下走。先排查（下方降级方案），修好再验证。

> **降级方案（`createLinkedBranch` 用不了时，如 GHES 老版本不支持、无写权限、变更报错）：**
> 不要卡死也不要假装绑上了。改为普通建分支并 push（`git checkout -b ai-feat-...-<编号>` → 推送），然后在收尾评论里**明确写清分支名**，并告诉用户"自动 linked branch 绑定未成功，可在 issue 的 Development 面板手动关联分支"。**已推分支时不要**再对同名 ref 调 `createLinkedBranch`（它是"创建"语义，对已存在的 ref 会报错）。

---

## Step 3 — 收尾（验证全过之后，先确认再动远程）

只对**已在本地修好、测试通过、且 linked branch 绑定已验证成功**的 issue 收尾。把下面这批远程写操作汇总给用户确认一次（可让用户选"逐个确认"或"本批一次性授权"），确认后**按顺序**执行——注意 **AISolved 标签和评论必须放到最后**。**若 Step 0.1 解析到 `--skip`，跳过这次汇总确认，直接按顺序执行**，但仍要把"正在做什么"用进度提示展示出来：

1. **推分支**（推到已绑定的那个 linked branch）：
   ```bash
   git push -u origin ai-feat-fix-login-crash-42
   ```

2. **自我 assign**：
   ```bash
   gh issue edit <num> --add-assignee @me
   ```

3. **收尾自检整体过一遍**（见下方清单）。**只有全部通过**才继续第 4 步。任何一项没过 → 回去补，不打标不评论。

4. **打 AISolved 标签 + 附方案评论（收尾的最后一步）**：
   ```bash
   # 标签不存在则先建，已存在忽略报错
   gh label create AISolved --color 5319e7 \
     --description "Resolved by AI agent, pending human review" 2>/dev/null || true
   gh issue edit <num> --add-label AISolved

   # 附方案评论（200~1000 字，结构见下方"评论内容要求"）
   gh issue comment <num> --body "<方案评论>"
   ```

> **绝不由 AI 关闭 issue。** 不带任何 `Closes/Fixes` 关闭关键字，不调 `gh issue close`。关不关由 owner 看完再定。

**评论内容要求**（控制在 **200～1000 字之间**——低于 200 字说明讲得太糊弄，超过 1000 字就别硬塞进评论，挪一部分到 commit message 里）：

**第一段：基础信息**（先讲清楚，缺一不可，各一句话）
- **根因**：到底是什么问题、对应 issue 描述/复现步骤里的哪一部分；
- **改了什么 / 怎么修的**：修复思路一句话概括；
- **已绑定的分支名**（不是 PR）。

**第二段起：详细说明**，从两个维度展开，让 owner 不用翻 diff 也能看懂改动全貌，按需分点：
- **模块维度**：改动涉及哪些模块/文件/分层（如 handler / service / dao，或具体到某个包/文件），每一层做了什么改动、为什么要动它，有没有涉及数据模型/接口变化。
- **函数维度**：具体新增或修改了哪些函数/方法，每个函数解决了 issue 里的哪部分问题，函数签名/调用方式有没有变化，调用链上受影响的上下游有哪些（谁调用了它、它调用了谁）。

**结尾**：@ 仓库 owner 请其 review。

一定要合理的分段

> 评论示例（200~1000 字区间，按此结构展开）：
> `根因：空 session 时未对 token 判空就直接跳转，触发空指针崩溃（对应 issue 复现步骤第 2 步）。修复思路：在跳转前补一层判空拦截，session 为空时回退登录页，同时补充空会话用例覆盖该路径。已推到关联分支 ai-feat-fix-login-crash-42（见本 issue Development 区）。`
> `模块层面：改动集中在 auth 模块的登录跳转链路——handler 层的 LoginHandler 收窄了对 session 结果的处理，service 层的 AuthService 新增了一次 token 有效性判断，两处改动都不涉及 dao 层，数据模型无变更。`
> `函数层面：新增 guardNullToken(session)，用于统一判空并返回是否需要回退登录页；LoginHandler.HandlePostLogin() 内部在原有跳转逻辑前插入了对 guardNullToken 的调用，函数签名未变，只是多了一次早退分支；新增测试 TestLogin_EmptySession 覆盖 session 为空的场景。调用链上除 LoginHandler 外没有其他调用方依赖被改动的返回值，不影响其余流程。`
> `@owner 麻烦 review，谢谢～`

---

## 收尾自检（每个 issue 做完对一遍，全过才允许打标 + 评论）
- [ ] 分支名符合 `ai-feat-<desc>-<编号>`（**连字符，无斜杠**）
- [ ] linked branch 绑定**已用第 3 步验证成功**（分支出现在 issue 的 linkedBranches 里）
- [ ] 有能覆盖该 bug 的测试且**已通过**
- [ ] 代码已 push 到该分支
- [ ] issue 的 assignee 含自己（@me）
- [ ] 未开 PR、未关闭 issue
- [ ] （最后）已打 `AISolved` 标签
- [ ] （最后）有一条 200~1000 字的评论，含根因/方案/分支名 + 模块维度说明 + 函数维度说明 + @owner review

全部处理完后，给用户一份小结：处理了哪几个、每个的分支名 / issue 链接、哪些跳过了（已分配 / 修不动 / 绑定失败）及原因。

---

## 注意事项 / 边界
- **依赖安装集中查 [INSTALL.md](./INSTALL.md)**：`git`/`gh`（必需）、`node`/`jq`（可选）的 macOS/Linux/Windows 安装命令、验证方式、常见报错处理都在这个文件里，Step 0 发现工具缺失时去查，别现场现编安装命令。
- **凭证红线**：只用 `gh`，永远不代替用户输入 token/密码/key；未登录只引导 `gh auth login`。
- **分支名不带斜杠**：一律 `ai-feat-<desc>-<编号>`。带 `/` 的分支名会让部分 `gh`/GraphQL 调用报错。
- **不开 PR、不关 issue**：本 Skill 只做到"分支改完 + 绑定 + 推送 + 打标评论"。是否开 PR、是否关闭 issue，都留给人。
- **绑定要验证**：linked branch 建完必须按第 3 步查一次 `linkedBranches` 确认，别假设成功。
- **打标评论放最后**：只有收尾自检全过（含绑定已验证、测试通过、已 push）才打 `AISolved` + 评论。
- **写操作先确认（除非 `--skip`）**：clone 仓库、创建 linked branch、push、评论、改 label/assignee 都会留下可见痕迹，动手前先让用户点头；用户传了 `--skip` 才可以跳过这些确认直接执行，但 `gh` 登录检查永远不受 `--skip` 影响。
- **进度提示不能省**：每切到一个新子步骤先输出 `[X/4] Step N · 在干什么`，`--skip` 只省确认动作，不省进度展示——用户看不到确认提示时，更需要靠进度提示知道跑到哪了。
- **`--issue` 指定的编号不一定都有效**：找不到（已关闭/不存在/是 PR）要弹警告并跳过、不能中断整批处理；已分配/已带 AISolved 标签的也要告知后跳过。
- **诚实优先**：没修好 / 没绑上就如实说，不硬贴 AISolved、不写夸大的"已解决"评论。
- **抢占检查放在最前**：选 issue 时 assignees 非空一律跳过，避免和已认领的人撞车；开工后若发现被人抢先，及时止损。
- **图谱会过期**：仓库有较大改动后，定位前先 `npx gitnexus analyze` 刷新一次。
- **Token 纪律**：能用图谱/`grep` 精准定位就别整目录 `cat`。
