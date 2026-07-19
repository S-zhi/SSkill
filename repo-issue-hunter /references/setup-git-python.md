# 安装 git 与 python3（本 Skill 的硬性前置依赖）

**何时读本文件**：Phase 0 的工具存在性检查发现 `git` 或 `python3` 缺失时。这两个是**必需**工具——`git` 用来定位仓库根目录、识别 remote；`python3` 用来跑 `scripts/` 下的所有脚本（`ci_bootstrap.py` / `check_graph.py` / `fingerprint.py` / `create_issue.py`）。缺任意一个，本 Skill 都无法运行。

> 其余依赖不在这里：`gh` / `GITHUB_TOKEN` 见 `references/setup-gh.md`；Node.js（GitNexus 用）见 `references/setup-gitnexus.md`。

---

## git

### macOS
```bash
xcode-select --install     # 方式一：系统自带路径最干净
brew install git           # 方式二：Homebrew
```

### Linux
```bash
sudo apt update && sudo apt install -y git     # Debian/Ubuntu
sudo dnf install -y git                         # Fedora/RHEL（较旧发行版用 yum）
sudo pacman -S git                              # Arch
```

### Windows
```powershell
winget install --id Git.Git -e --source winget
# 或： choco install git -y
# 或手动下载： https://git-scm.com/download/win
```

### 验证
```bash
git --version
```

### 常见报错
- `xcode-select: error: command line tools are already installed` → 已装过，忽略即可。
- Linux `E: Unable to locate package` → 先 `sudo apt update` 再重试；企业内网检查代理/镜像源。
- 装完新终端仍 `command not found` → PATH 未刷新，重开终端或 `source ~/.zshrc` / `~/.bashrc`。

---

## python3

### macOS
```bash
brew install python@3.12
# macOS 通常自带 python3，先跑 `python3 --version` 确认版本是否够新（建议 >=3.9）
```

### Linux
```bash
sudo apt install -y python3 python3-pip     # Debian/Ubuntu
sudo dnf install -y python3 python3-pip     # Fedora/RHEL
sudo pacman -S python python-pip            # Arch
```

### Windows
```powershell
winget install --id Python.Python.3.12 -e --source winget
# 或： choco install python -y
# 或手动下载： https://www.python.org/downloads/windows/
```
> Windows 安装向导里务必勾选 **Add python.exe to PATH**，否则装完命令行还是找不到。

### 验证
```bash
python3 --version
# Windows 有些环境命令是 `python` 而非 `python3`，两个都试一下
```

### 常见报错
- Linux 发行版自带的是 `python3` 而没有裸 `python` 命令 → 本 Skill 的脚本一律用 `python3 <skill>/scripts/xxx.py` 调用，不依赖裸 `python`。
- Windows 装完 `python3` 不认，但 `python` 认 → 检查安装时有没有勾选 "Add to PATH"，或直接把 SKILL.md 里的 `python3` 换成 `python` 执行。
- `pip`/`pip3` 缺失不影响本 Skill——脚本只用标准库，不需要额外装包。

---

## 环境完全无法安装时

`git` 或 `python3` 缺失且装不了 → **硬阻塞**，如实告知用户缺什么、为什么必需，然后停止，不要假装能绕过继续执行 Phase 1 及之后的步骤。
