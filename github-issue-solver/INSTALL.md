# GitHub Issue Solver 依赖安装指南

本文件集中存放 [SKILL.md](./SKILL.md) 依赖的命令行工具安装方式，供 **Step 0 前置条件校验**发现工具缺失时查阅使用。按"工具 → 是否必需 → 各平台安装命令 → 验证 → 常见报错处理"组织，覆盖 macOS / Linux / Windows 三个平台。

## 依赖一览

| 工具 | 是否必需 | 用途 | 缺失后果 |
|---|---|---|---|
| git | 必需 | 克隆仓库、创建分支、提交 | 无法进行任何本地操作，Skill 无法运行 |
| gh（GitHub CLI） | 必需 | 所有 GitHub 读写操作（issue、label、linked branch 等） | Skill 核心功能完全不可用 |
| node.js（含 npx） | 可选 | 运行 GitNexus 建立知识图谱、加速定位代码 | 退回手动读码定位（SKILL.md Step 2b 降级方案），变慢但不阻塞 |
| jq | 可选 | Step 1 的 JSON 过滤/排序小抓手 | 手动肉眼筛选 issue 列表，变慢但不阻塞 |

> **安装前必须先确认**：下面的命令大多需要 `sudo` / 管理员权限，或会修改系统包管理器状态（brew / apt / winget 等），属于**会在系统层面留下改动的操作**。执行前，按 SKILL.md 正文的规则向用户展示具体命令、拿到明确同意后再执行；装完要重新跑一遍验证命令，确认真的可用了再继续后续步骤。

---

## git

### macOS
```bash
# 方式一：Xcode Command Line Tools（推荐，系统自带路径最干净）
xcode-select --install

# 方式二：Homebrew
brew install git
```

### Linux
```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y git

# Fedora / RHEL / CentOS
sudo dnf install -y git   # 较旧版本用 yum 替换 dnf

# Arch
sudo pacman -S git
```

### Windows
```powershell
# 方式一：winget（Win10 1709+ / Win11 自带）
winget install --id Git.Git -e --source winget

# 方式二：Chocolatey
choco install git -y

# 方式三：手动下载安装包
# https://git-scm.com/download/win
```

### 验证
```bash
git --version
```

### 常见报错处理
- `xcode-select: error: command line tools are already installed` → 已装过，忽略，直接验证。
- Linux `E: Unable to locate package` → 先 `sudo apt update` 再重试；企业内网环境检查是否有代理/镜像源配置问题。
- Windows 提示找不到 `winget` → Win10 需先从 Microsoft Store 更新"应用安装程序"，或改用 Chocolatey / 手动安装包。
- 装完后 `git --version` 仍报 `command not found` → 新终端未重新加载 PATH，重启终端或 `source ~/.zshrc` / `source ~/.bashrc`。

---

## gh（GitHub CLI）

### macOS
```bash
brew install gh
```

### Linux
```bash
# Debian / Ubuntu（官方仓库，避免装到过时版本）
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -nv -O- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update \
  && sudo apt install gh -y

# Fedora / RHEL / CentOS
sudo dnf install -y 'dnf-command(config-manager)'
sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
sudo dnf install -y gh

# Arch
sudo pacman -S github-cli
```

### Windows
```powershell
winget install --id GitHub.cli -e --source winget
# 或
choco install gh -y
```

### 验证 + 登录
```bash
gh --version
gh auth login   # 按提示选 GitHub.com → HTTPS/SSH → 浏览器授权，完成后 gh auth status 应显示已登录
```

### 常见报错处理
- `gh: command not found`（装完立刻测）→ 开一个新终端窗口，PATH 缓存未刷新。
- apt 报 `NO_PUBKEY` / GPG 签名错误 → 官方 key 没导入成功，重新执行上面 `wget ... keyring` 那一行，检查网络是否能访问 `cli.github.com`。
- `gh auth login` 卡在"浏览器打不开"（纯 SSH / 无桌面环境）→ 选 "Paste an authentication token" 方式，去 GitHub 网页生成 PAT（Settings → Developer settings → Personal access tokens）手动粘贴——**这一步必须用户自己在浏览器操作**，Skill/Claude 不代为生成、读取或输入 token。
- 公司内网/代理环境下 `gh auth login` 超时 → 检查 `HTTPS_PROXY` / `HTTP_PROXY` 环境变量是否配置正确。
- `gh` 已登录但仍报权限不足（403）→ 检查登录账号是否对目标仓库有相应权限（读/写），不是安装问题，是账号权限问题，无法通过重装解决。

---

## node.js（GitNexus 依赖，可选）

### macOS
```bash
brew install node
```

### Linux
```bash
# 推荐用 nvm，避免权限问题和版本冲突
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc   # 或 ~/.zshrc，取决于你的 shell
nvm install --lts

# 或发行版包管理器（版本可能较旧，不推荐用来跑 GitNexus）
sudo apt install -y nodejs npm   # Debian/Ubuntu
sudo dnf install -y nodejs npm   # Fedora/RHEL
```

### Windows
```powershell
winget install --id OpenJS.NodeJS.LTS -e --source winget
# 或
choco install nodejs-lts -y
```

### 验证
```bash
node --version
npx --version
```

### 常见报错处理
- `npx gitnexus analyze` 在 npm 11.x 下安装崩溃 → 改用 SKILL.md 正文提到的降级命令：
  ```bash
  pnpm --allow-build=@ladybugdb/core --allow-build=gitnexus --allow-build=tree-sitter dlx gitnexus@latest analyze
  ```
  需要先有 pnpm：`npm install -g pnpm` 或 `brew install pnpm`。
- Linux 上 `sudo npm install -g xxx` 权限报错 → 别用 sudo 硬装，改用 nvm 管理 node，从根源避免全局包权限问题。
- 装完 node 后 `npx` 仍提示找不到命令 → 确认 PATH 里包含 nvm 管理的 node 路径（`nvm which node` 所在目录），新终端重试。
- 公司网络屏蔽 npm 官方源，`npx gitnexus analyze` 卡住/超时 → 配置国内镜像：`npm config set registry https://registry.npmmirror.com`，再重试。
- node 装不上或环境完全禁止安装 → 不阻塞主流程，直接走 SKILL.md Step 2b 的降级方案（手动 grep + 阅读代码定位），继续走完 issue 处理流程。

---

## jq（可选）

### macOS
```bash
brew install jq
```

### Linux
```bash
sudo apt install -y jq     # Debian/Ubuntu
sudo dnf install -y jq     # Fedora/RHEL
sudo pacman -S jq          # Arch
```

### Windows
```powershell
winget install --id jqlang.jq -e --source winget
# 或
choco install jq -y
```

### 验证
```bash
jq --version
```

### 常见报错处理
- Windows 装完 `jq` 在普通 cmd 里不认 → 确认在 PowerShell / Git Bash 里执行，或重启终端刷新 PATH。
- 没装 jq 也不必强求安装 → Step 1 的排序小抓手只是"锦上添花"，缺失时直接看 `gh issue list --json number,title,assignees,labels` 的原始输出肉眼筛选（按 number 升序、跳过 assignees 非空、跳过已带 AISolved 标签的）即可，不阻塞流程。

---

## 环境完全无法安装时的兜底策略

如果用户所在环境是沙箱、离线、或没有安装权限，按工具的必需程度区别处理：

- **git 或 gh 缺失且装不了** → 硬阻塞，Skill 依赖 `gh` 完成所有 GitHub 读写、依赖 `git` 完成本地分支操作，两者任一缺失都无法运行。如实告知用户具体缺什么、为什么必需，然后停止，不要假装能绕过去继续执行后续步骤。
- **node 缺失且装不了** → 不阻塞，直接走 SKILL.md Step 2b 的 GitNexus 降级方案（纯手动定位代码），继续走完流程。
- **jq 缺失且装不了** → 不阻塞，手动筛选 issue 列表，继续走完流程。
