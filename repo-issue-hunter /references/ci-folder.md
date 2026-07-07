# `.ci` 文件夹说明（状态存储 + 去重）

`.ci` 建在**被分析仓库的根目录**下，是本 Skill 的持久化记忆：它记住“这个仓库已经建过哪些 issue、图谱建到哪个提交”，从而让 Skill 可反复运行而不重复建单、不重复建图。

Skill 一被触发，Phase 0 就先读它（`ci_bootstrap.py`）。

## 目录结构
```
.ci/
├── README.md                 # 一句话说明这个文件夹是干嘛的（自动生成）
├── config.json               # 可选配置：默认 labels、repo 覆盖等（自动生成模板）
├── graph/
│   └── indexed.json          # GitNexus 建图标记：{ head, indexed_at, gitnexus_version }
└── issues/
    ├── created.jsonl         # 已创建 issue 的压缩记录（去重真相来源，每行一条）
    └── created.jsonl.gz      # 可选：--gzip 时额外产出的压缩快照
```

## 去重记录（`issues/created.jsonl`）
每成功创建一个 issue，追加一行**压缩后的指纹记录**（只留去重必需的信息，不存完整正文）：
```json
{"fp":"a1b2c3d4e5f6a7b8","type":"bug","title":"【Bug Request】…","number":123,"url":"https://github.com/o/r/issues/123","at":"2026-07-06T09:00:00Z"}
```
- `fp`：指纹，对“去掉【】前缀、小写化、去标点、压缩空白”后的标题（+ 可选正文）做 sha256 取前 16 位十六进制。
- 这就是所谓“把 issue 压缩后存储”：一条完整 issue → 一行紧凑指纹记录。

## 去重是怎么生效的
1. **Phase 0** 读出所有已建 issue 的标题列表，作为本轮基线。
2. **Phase 3** 收敛候选时，与基线做**语义去重**（措辞不同但本质相同也算重复）。
3. **Phase 5** `create_issue.py` 建单前再做两道机器去重：
   - **本地**：候选指纹是否已在 `created.jsonl` 里 → 命中则跳过。
   - **远端**：GitHub 上是否已有同名 issue → 命中则跳过。
4. **Phase 6** 建成功后自动追加新指纹记录。

三层（语义 + 本地指纹 + 远端检索）叠加，保证同一个问题不会被重复建单。

## 幂等性
- 记录以“追加一行”的方式写入，天然幂等、可安全重跑。
- **不要手动编辑 `issues/created.jsonl`**——它是去重的真相来源，改坏了会导致重复建单或漏建。
- 想“重置去重记忆”（比如故意重建某些 issue）时，再谨慎删除对应行，并向用户确认。

## 建图标记（`graph/indexed.json`）
```json
{ "head": "<建图时的 git HEAD sha>", "indexed_at": "<ISO 时间>", "gitnexus_version": "<版本或 unknown>" }
```
- `check_graph.py` 对比“标记里的 head”与“当前 HEAD”：一致 → `skip` 复用；不一致或无标记 → `rebuild`。
- 建完图后用 `check_graph.py --mark` 刷新此标记。

## 要不要提交进 git？
- 默认建议把 `.ci/` **提交进版本库**，这样团队/多机共享去重记忆。
- 若不想入库，可在 `.gitignore` 里忽略 `.ci/`（但那样去重记忆只在本机有效）。由用户决定，Skill 不擅自改 `.gitignore`。
