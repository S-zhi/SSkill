# GitHub 建单参考（gh CLI + REST API）

Phase 5 用官方接口创建 issue。`create_issue.py` 已封装好这套逻辑；本文件解释它背后用什么、如何鉴权、如何排错，方便你在脚本失败时定位。

---

## 鉴权（二选一，脚本会自动探测）

**方式 A：`gh` CLI（优先）**
- 前提：本机已装 `gh` 且 `gh auth status` 显示已登录。
- 优点：不用手动管 token，`gh` 自己处理鉴权与仓库上下文。
- 脚本优先走这条：`gh issue create --title ... --body-file ... --label ...`。

**方式 B：REST + `GITHUB_TOKEN`（回退）**
- 环境变量 `GITHUB_TOKEN` 提供一个有 **issues 写权限**的 token：
  - 细粒度 token：对目标仓库授予 `Issues: Read and write`。
  - 经典 token：`repo`（私有仓库）或 `public_repo`（公开仓库）。
- **绝不要把 token 明文写进代码、issue 正文或 URL 参数**；只从环境变量读。

> 若两者都不可用，`create_issue.py` 会报错并退出。此时把 issue 内容直接交给用户，让其自行创建，并说明缺 `gh` 登录或 `GITHUB_TOKEN`。

---

## REST 接口速览（脚本内部使用）

**创建 issue**
```
POST https://api.github.com/repos/{owner}/{repo}/issues
Headers:
  Authorization: Bearer <GITHUB_TOKEN>
  Accept: application/vnd.github+json
  X-GitHub-Api-Version: 2022-11-28
Body (JSON):
  { "title": "…", "body": "…", "labels": ["bug"] }
```
- 成功：`201 Created`，返回体含 `number` 与 `html_url`（脚本用它写进 `.ci` 记录）。

**去重用的检索（创建前查重）**
```
GET https://api.github.com/search/issues?q=repo:{owner}/{repo}+in:title+type:issue+"<标题去掉【】前缀>"
```
- 命中已存在的同名 issue（open 或 closed）→ 跳过创建，避免远端重复。
- `gh` 等价物：`gh issue list --state all --search "in:title <标题>"`。

---

## 仓库识别
- 默认从 `git remote get-url origin` 解析 `owner/repo`，支持两种形式：
  - `git@github.com:owner/repo.git`
  - `https://github.com/owner/repo(.git)`
- 也可用 `--repo owner/name` 显式覆盖。

---

## 标签（labels）
- Bug 默认 `bug`，Feature 默认 `enhancement`（GitHub 新仓库自带这两个标签）。
- 可用 `--label` 覆盖/追加（可重复）。若目标仓库没有该标签，REST 会报 422；脚本会提示，可先去仓库建标签或改用已存在的标签。

---

## 常见错误与排查
| 现象 | 可能原因 | 处理 |
|---|---|---|
| `401 Unauthorized` | token 无效/过期 | 换有效 token，或改用 `gh auth login` |
| `403 Forbidden` / rate limit | 权限不足 / 触发限流 | 确认 token 有 issues 写权限；限流则稍后重试 |
| `404 Not Found` | 仓库名错 / 无权访问私有仓库 | 核对 `--repo`；私有仓库需 `repo` scope |
| `422 Unprocessable` | 标签不存在 / 字段非法 | 先在仓库建对应标签，或去掉 `--label` |
| `gh: command not found` | 未装 gh | 见 `setup-gh.md`：装 `gh` 或改用 `GITHUB_TOKEN` 走 REST |

---

## 安全边界（务必遵守）
- **建 issue 前必须经用户明确确认**（Phase 5 的空跑 + 确认）。这属于“在仓库发布内容”的副作用操作。
- 只创建本轮经用户看过的 issue，不要因为脚本能跑就批量自动建。
- token 只从环境变量读，不落盘、不进日志、不进 issue 正文。
- 创建成功后由脚本写 `.ci` 记录；不要手改 `.ci/issues/` 下的文件。
