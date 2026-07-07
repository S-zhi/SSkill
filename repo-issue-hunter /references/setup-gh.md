# 安装并配置 GitHub CLI（`gh`）

**何时读本文件**：Phase 5 建单前，`create_issue.py` 探测到既没有可用的 `gh`、也没有 `GITHUB_TOKEN`（`auth: null`），或用户机器上 `gh: command not found` / `gh auth status` 未登录时。按本文档装好其一即可继续建单。

建单需要“能创建 issue 的鉴权”，二选一：**A) 装并登录 `gh`（推荐）**，或 **B) 只配 `GITHUB_TOKEN` 走 REST**。任选一条走通即可，不必两条都做。

---

## 方案 A：安装并登录 `gh`（推荐）

### 1. 安装
- **macOS（Homebrew，Apple Silicon / Intel 通用）**
  ```bash
  brew install gh
  ```
- **Linux**
  - Homebrew：`brew install gh`
  - Debian / Ubuntu（官方 apt 源）：
    ```bash
    (type -p wget >/dev/null || sudo apt install wget -y) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update && sudo apt install gh -y
    ```
  - Fedora / RHEL：`sudo dnf install gh`；Arch：`sudo pacman -S github-cli`
- **Windows**
  ```powershell
  winget install --id GitHub.cli
  # 或： scoop install gh   /   choco install gh
  ```

装完验证：
```bash
gh --version
```

### 2. 登录
```bash
gh auth login
```
交互式选择：
1. `GitHub.com`
2. 协议选 `HTTPS`
3. `Login with a web browser`（或 `Paste an authentication token` 粘贴一个 PAT）
4. 按提示在浏览器完成授权

确认已登录（这是 `create_issue.py` 判定“gh 可用”的依据）：
```bash
gh auth status
```
看到 `Logged in to github.com` 即可。若要确保有建 issue 的权限，可补授权：
```bash
gh auth refresh -s repo        # 私有仓库；公开仓库用 -s public_repo
```

登录成功后**不用配任何 token**，直接回到 Phase 5 建单即可。

---

## 方案 B：不装 gh，只配 `GITHUB_TOKEN`（REST 回退）

适合无法/不想装 gh 的环境。脚本在没有 gh 时会自动改用 REST + 环境变量里的 token。

### 1. 生成 token（二选一）
- **细粒度 PAT（推荐）**：GitHub → Settings → Developer settings → Fine-grained tokens → 选中目标仓库 → 授予 **Issues: Read and write**。
- **经典 PAT**：勾选 `repo`（私有仓库）或 `public_repo`（仅公开仓库）。

### 2. 注入环境变量
```bash
export GITHUB_TOKEN=ghp_你的token
# 想持久化可写进 ~/.zshrc 或 ~/.bashrc，但注意不要提交进版本库
```
脚本也接受 `GH_TOKEN` 作为等价变量。

### 3. 验证 token 有效
```bash
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user | head
```
能返回你的用户信息即有效。

---

## 安全须知
- **token 只放进环境变量**，绝不写进代码、issue 正文、`.ci` 记录或 URL 参数。
- 建 issue 前仍要走 Phase 5 的 `--dry-run` + 用户确认，不因鉴权就绪就自动批量建单。
- 若两条都不方便配，把 issue 内容直接交给用户，让其在网页手动创建。
