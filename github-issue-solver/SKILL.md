---
name: github-issue-solver
description: 自动检索并批量解决 GitHub 仓库的 Open Issue（当前仓库或用户指定的仓库）。每批默认处理 3 个、最多 5 个，从编号最小的、且 assignees 为空的 Open Issue 里挑；对每个 issue 建一个绑定到该 issue 的 ai-feat- 分支（连字符、不带斜杠）、定位相关代码（优先用 GitNexus 加速）、分阶段修改并写测试验证；全部验证通过后再自我 assign、打上 AISolved 标签、附一条 200 字内的方案评论并请求 owner review。不发起 PR、不关闭 issue。全程用 gh CLI 操作、绝不碰本地密钥，未登录时引导用户 gh auth login。当用户说"帮我处理一下这个仓库的 issue""解决几个 issue""自动修一批 bug""看看有哪些 issue 能修""处理 issue #12 #15"或给出一个 GitHub 仓库希望自动分诊+修复时，就应主动使用本 Skill——即使没有明说"用 Skill"也要触发。Use this whenever the user wants to automatically triage and fix GitHub issues in a repo, resolve a batch of issues, or work through the open-issue backlog with branches, tests, labels and review requests.
---

# GitHub Issue Solver（自动分诊 + 修复 Open Issue）

把一个仓库的 Open Issue 变成"已修复、有分支、有测试、待人工 review"的状态。核心是一条可重复的流水线：**筛选 → 逐个修 → 收尾（远程写操作前先确认）**。

**三条贯穿始终的原则：**
- **只用 `gh`，绝不碰密钥**：所有 GitHub 操作走 `gh` CLI（它复用用户已登录的凭证）。永远不要读取、写入或要求用户粘贴 token / 密码 / API key。未登录就引导登录，绝不代替用户输入凭证。
- **不开 PR，只做到分支**：本 Skill **不发起 PR**。职责边界是"把 issue 在一个绑定好的分支上改完、测好、推上去"，是否开 PR / 合并由人来决定。
- **远程写操作前先确认**：push、创建 linked branch、评论、改 label / assignee 都是对仓库可见的写操作。本地准备好（分支、提交、测试通过）之后、真正动远程之前，把"将要做什么"汇总给用户，拿到明确同意再执行（见 Step 3）。
- **验证通过才收尾打标**：`AISolved` 标签和方案评论**放到最后**——只有分支已可靠绑定、测试通过、代码已推上去、收尾自检全过之后才打标 + 评论。修不动或没把握就如实说明、保留分支交人工，不假装解决了。**任何情况下都不由 AI 关闭 issue**（关不关由 owner 决定）。

---

## Step 0 — 前置检查（登录 + 定位仓库）

1. **确认 `gh` 已登录**：
   ```bash
   gh auth status
   ```
   - 未登录（命令报错 / 提示 not logged in）→ **不要**自己去找 token，直接引导用户：
     > 请在终端运行 `gh auth login`，按提示用浏览器完成 GitHub 授权后再继续。
   - 已登录 → 继续。

2. **定位目标仓库**：
   - 用户**没指定** → 默认当前目录所在仓库。确认它有 GitHub remote：`gh repo view --json nameWithOwner -q .nameWithOwner`。
   - 用户**给了仓库**（`owner/repo` 或 URL）且本地没有 → 先 `cd` 到合适的父目录，`gh repo clone owner/repo` 再 `cd` 进去（**clone 前向用户确认一次**，属于会在磁盘上落东西的操作）。
   - 后续所有 `gh` 命令若不在仓库目录内，统一带 `-R owner/repo`。

3. **记下仓库 owner**（收尾请 review、@ 提及时要用）：
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
   - 用户**未指定编号** → 从筛选后的列表里取编号最小的 **N** 个，默认 **N=3**，**上限 5**。
   - 用户**指定了编号**（如"处理 #12 #15 #20"）→ 就用这些；仍要逐个检查 assignees，若某个已被分配，**默认跳过并告知用户**（除非用户明确要求照做）。指定超过 5 个时提醒并只取前 5 个。

4. **把选中的 issue 列给用户确认**（编号 + 标题 + 链接），得到"开始"再进入 Step 2。这一步很轻，但能避免选错仓库/选错 issue 白干一场。

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

只对**已在本地修好、测试通过、且 linked branch 绑定已验证成功**的 issue 收尾。把下面这批远程写操作汇总给用户确认一次（可让用户选"逐个确认"或"本批一次性授权"），确认后**按顺序**执行——注意 **AISolved 标签和评论必须放到最后**：

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

   # 附方案评论（200 字以内）
   gh issue comment <num> --body "<方案评论>"
   ```

> **绝不由 AI 关闭 issue。** 不带任何 `Closes/Fixes` 关闭关键字，不调 `gh issue close`。关不关由 owner 看完再定。

**评论内容要求**（控制在 **200 字以内**）：
- 一句话说清**根因**；
- 一句话说清**改了什么 / 怎么修的**；
- 指明**已绑定的分支名**（不是 PR）；
- 结尾 @ 仓库 owner 请其 review。

> 评论示例（照此风格，别超 200 字）：
> `根因：空 session 时未判空直接跳转导致崩溃。修复：在跳转前对 token 判空并回退到登录页，已补充空会话用例。已推到关联分支 ai-feat-fix-login-crash-42（见本 issue Development 区）。@owner 麻烦 review，谢谢～`

---

## 收尾自检（每个 issue 做完对一遍，全过才允许打标 + 评论）
- [ ] 分支名符合 `ai-feat-<desc>-<编号>`（**连字符，无斜杠**）
- [ ] linked branch 绑定**已用第 3 步验证成功**（分支出现在 issue 的 linkedBranches 里）
- [ ] 有能覆盖该 bug 的测试且**已通过**
- [ ] 代码已 push 到该分支
- [ ] issue 的 assignee 含自己（@me）
- [ ] 未开 PR、未关闭 issue
- [ ] （最后）已打 `AISolved` 标签
- [ ] （最后）有一条 ≤200 字、含方案 + 分支名 + @owner review 的评论

全部处理完后，给用户一份小结：处理了哪几个、每个的分支名 / issue 链接、哪些跳过了（已分配 / 修不动 / 绑定失败）及原因。

---

## 注意事项 / 边界
- **凭证红线**：只用 `gh`，永远不代替用户输入 token/密码/key；未登录只引导 `gh auth login`。
- **分支名不带斜杠**：一律 `ai-feat-<desc>-<编号>`。带 `/` 的分支名会让部分 `gh`/GraphQL 调用报错。
- **不开 PR、不关 issue**：本 Skill 只做到"分支改完 + 绑定 + 推送 + 打标评论"。是否开 PR、是否关闭 issue，都留给人。
- **绑定要验证**：linked branch 建完必须按第 3 步查一次 `linkedBranches` 确认，别假设成功。
- **打标评论放最后**：只有收尾自检全过（含绑定已验证、测试通过、已 push）才打 `AISolved` + 评论。
- **写操作先确认**：clone 仓库、创建 linked branch、push、评论、改 label/assignee 都会留下可见痕迹，动手前先让用户点头。
- **诚实优先**：没修好 / 没绑上就如实说，不硬贴 AISolved、不写夸大的"已解决"评论。
- **抢占检查放在最前**：选 issue 时 assignees 非空一律跳过，避免和已认领的人撞车；开工后若发现被人抢先，及时止损。
- **图谱会过期**：仓库有较大改动后，定位前先 `npx gitnexus analyze` 刷新一次。
- **Token 纪律**：能用图谱/`grep` 精准定位就别整目录 `cat`。
