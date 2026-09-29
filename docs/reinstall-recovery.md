# 重装系统前后恢复指南

本指南只覆盖此仓库的代码与本地开发环境，不是整台 Mac 的备份。当前代码以 GitHub `main` 为主要恢复源；重装前必须在另一台设备、外接磁盘或可信的加密云盘上保留经过校验的备份。仅把 bundle 放在待抹盘电脑的桌面上，不能抵御系统重装。

## 重装前

1. 确认 `git status --short --branch` 没有未提交改动，`git fetch origin` 后检查 `git log --oneline origin/main..main`；有待推送提交时先正常推送。其他本地分支、标签或未跟踪文件要逐项核对，GitHub 上的 `main` 不一定包含它们。
2. 在仓库外执行 `git bundle create /安全的备份位置/bot.bundle --all`，再运行 `git bundle verify /安全的备份位置/bot.bundle`、`shasum -a 256 /安全的备份位置/bot.bundle`。把 bundle 和校验值复制到独立介质，并在该介质上重新计算散列；不要只验证源文件。bundle 只包含 Git 历史，不包含被忽略的文件。
3. 在受控的加密备份中单独处理 `.env`、实际使用的数据库、部署平台配置和凭据。若使用 SQLite，停止写入服务后备份数据库，或使用 SQLite 的一致性备份功能；不要把数据库、Telegram 会话、Bot Token、API Key、加密密钥或 SSH 私钥提交 Git/放入公开网盘。恢复旧数据库中的 Telegram 加密字段时，必须保留原 `CONFIG_ENCRYPTION_KEY`；未显式设置时还必须保留用于派生密钥的原 `SECRET_KEY`。
4. 检查其他工作目录、个人文件及工具配置是否已有独立备份。GitHub 仓库和本项目 bundle 不能代替整机备份。抹盘前从独立设备或介质确认文件可读取、散列一致，并确认 GitHub 登录和必要的双因素恢复方式可用。

## 重装后

安装 Git、Python 3.11+、`uv`、Node.js 22.22.0 和 pnpm 10.33.0。需要仓库操作时重新登录 GitHub；SSH 凭据只能从受控备份恢复或重新生成，不要从公开文档获取。

```bash
git clone https://github.com/shiyi-log/bot.git
cd bot
uv sync --locked
cd frontend
pnpm install --frozen-lockfile
cd ..
```

若需要本地环境变量，从 `.env.example` 创建本地 `.env`，把凭据从安全存储单独恢复；不使用真实网络时保留三个 `ENABLE_*_NETWORK=0` 开关。先决定是否恢复旧数据库：需要旧业务数据时先选择对应数据库并恢复原加密密钥，按实际数据库类型制定一致性恢复步骤，再检查是否需要执行迁移；没有旧数据时才在新库运行 `uv run python manage.py migrate`。当前模板的 `db.sqlite3` 仅在本地使用，Git 不备份它。

```bash
uv run python manage.py test botcore.tests
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
cd frontend
pnpm --filter @vben/web-antd typecheck
pnpm --filter @vben/web-antd build
```

上述命令只验证离线逻辑与构建，不验证真实 Telegram/TRON、生产环境或数据恢复。开发启动入口为 `./scripts/start-dev.sh`，默认前端 `5173`、后端 `8010`；其运行前会执行迁移，恢复旧数据库前不要先启动它。

如 GitHub 不可用，可从校验通过的 bundle 恢复：`git clone /安全的备份位置/bot.bundle bot`。Git bundle 的本地分支可用 `git bundle list-heads /安全的备份位置/bot.bundle` 核对；克隆后需重新配置远端，再审慎恢复其他分支。若备份的是历史清理前的旧 bundle，它可能含已从公开仓库移除的敏感日志，必须当机密材料保管，不可重新推送到公开远端。
