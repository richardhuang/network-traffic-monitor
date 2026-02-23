# 推送到 GitHub 的步骤

## 方式一：使用 GitHub CLI（推荐）

### 1. 安装 GitHub CLI（如果未安装）

```bash
brew install gh
```

### 2. 登录 GitHub

```bash
gh auth login
```

### 3. 创建仓库并推送

```bash
cd /Users/rhuang/workspace/tools/network

# 创建仓库（私有或公开）
gh repo create network-traffic-monitor --public --source=. --remote=origin --push

# 或者创建私有仓库
gh repo create network-traffic-monitor --private --source=. --remote=origin --push
```

---

## 方式二：使用 Git 命令

### 1. 在 GitHub 上创建仓库

访问 https://github.com/new

- Repository name: `network-traffic-monitor`
- 选择 Public 或 Private
- **不要** 勾选 "Add a README file"
- 点击 "Create repository"

### 2. 推送代码

```bash
cd /Users/rhuang/workspace/tools/network

# 添加远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin git@github.com:YOUR_USERNAME/network-traffic-monitor.git

# 或者使用 HTTPS
git remote add origin https://github.com/YOUR_USERNAME/network-traffic-monitor.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

---

## 方式三：使用 GitHub Desktop

1. 下载并安装 GitHub Desktop: https://desktop.github.com/
2. 打开 GitHub Desktop
3. 选择 `File` → `Add Local Repository`
4. 选择 `/Users/rhuang/workspace/tools/network` 目录
5. 点击 `Publish repository`
6. 输入仓库名称 `network-traffic-monitor`
7. 点击 `Publish`

---

## 验证推送

推送完成后，访问：
```
https://github.com/YOUR_USERNAME/network-traffic-monitor
```

---

## 后续更新

```bash
# 提交更改
git add .
git commit -m "描述你的更改"

# 推送到 GitHub
git push
```
