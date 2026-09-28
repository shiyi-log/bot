# 项目台账

## 2026-09-27T02:06:51+08:00 — 建立离线 CI 工作流基线

- 状态 / Status: 进行中
- 目标 / Goal: 将 README 中现有 Django 与 Vben 离线验证命令接入 GitHub Actions；仅触发 `main` 推送、拉取请求和手动运行，不部署、不使用业务密钥或真实 Telegram/TRON 网络。
- 基线 / Baseline: `/Users/a399/Desktop/data/bot`，分支 `main`，HEAD `792d27b8bcf6a76b269145ff627be284a1193c6f`；修改前 `git status --short --branch` 为 `## main...origin/main`，没有已知本地改动；时钟使用系统时钟 `Asia/Shanghai`（UTC+08:00），对应 UTC `2026-09-26T18:06:51Z`。
- 读取 / Read: `AGENTS.md`、`skills/telegram-tron-bot/SKILL.md` — 项目规则、外部网络默认关闭和版本记录要求；`README.md`、`docs/backend-api.md` — 现有离线命令与权限边界；`pyproject.toml`、`uv.lock`、`config/settings.py` — Python >=3.11、锁定依赖与默认 SQLite；`frontend/package.json`、`frontend/apps/web-antd/package.json`、`frontend/.node-version`、`frontend/pnpm-lock.yaml`、`frontend/.npmrc` — Node 22.22.0、pnpm 10.33.0 和 typecheck/build 命令；`CHANGELOG.md`、`docs/version-record.md` — 现有发布记录格式；只读查询 GitHub 官方 action 版本与使用说明。
- 范围 / Scope: 新增 `.github/workflows/ci.yml`，补充 `README.md`、`CHANGELOG.md`、`docs/version-record.md`，在本台账追加验证和恢复记录；不修改业务代码、数据库、密钥、运行服务或远端仓库。
- 修改 / Write: `docs/project-ledger.md` — 新建这份基线记录；可通过删除本次新文件回退，但须保留此前存在的其他用户内容。
- 时间逻辑 / Time logic: GitHub 事件时间由平台负责；本工作流不解析业务时间戳，无定时边界或重试策略；本记录以 `Asia/Shanghai` 带偏移的时间标识操作顺序。
- 验证 / Verification: 初始 Git 状态与版本命令均只读；GitHub 托管 runner 的真实执行尚未运行，不能从本地推断成功。
- 利用 / Reuse: CI 配置以仓库锁文件与已有命令为来源；必要时删除新工作流并回退本次文档增量，本地未推送前远端无变化。
- 下一步 / Next: 完成工作流测试先红后绿、执行本地后端与前端门禁、记录局限和结果。

## 2026-09-27T02:09:00+08:00 — 新增 GitHub Actions 工作流

- 状态 / Status: 进行中
- 读取 / Read: GitHub 官方 `actions/checkout`、`actions/setup-node`、`astral-sh/setup-uv`、`pnpm/action-setup` 已发布版本与固定提交；`rhysd/actionlint` v1.7.12 发行包及官方校验和一致。
- 修改 / Write: `.github/workflows/ci.yml` — 新建 `main` 推送、PR 和手动触发的双任务门禁；Django 离线测试/检查/迁移漂移，Vben 类型检查/构建，依赖按锁文件安装、action 固定提交、工作流只读权限与外部业务网络开关显式关闭；可删除本次新增文件回退。`docs/project-ledger.md` — 追加本条写入及验证记录；可回退本次增量。
- 验证 / Verification: 写工作流前 `/tmp/bot-ci-actionlint.ovdfvn/actionlint .github/workflows/ci.yml` → 退出码 3，因文件缺失而失败；写入后加 `-color` 运行相同目标 → 退出码 0、没有诊断；这只是本机静态校验，不是 GitHub Actions 运行。
- 限制 / Limits: 远端默认分支仍是 `master`，本次文件在 `main`；GitHub 托管 runner 和手动触发尚未执行，也未修改远端设置。
- 下一步 / Next: 跑锁定依赖的本地后端与前端命令，补充用户文档和最终结果。

## 2026-09-27T02:16:48+08:00 — 离线 CI 本地验证与交付边界

- 状态 / Status: 完成（工作流与本地门禁）；GitHub 托管 CI 未运行。
- 读取 / Read: `.github/workflows/ci.yml` — 复查事件、权限、三个业务网络开关、锁文件命令和两任务边界；`README.md`、`CHANGELOG.md`、`docs/version-record.md` — 核对文档仅记录本地结果；`git status --short --branch` — 修改范围仅为本次五个项目文件；远端仓库元数据只读确认默认分支为 `master`。
- 修改 / Write: `README.md` — 新增 CI 触发、两个检查任务、网络隔离及手动触发的默认分支限制；`CHANGELOG.md`、`docs/version-record.md` — 追加未发布 CI 说明及已验证/未验证边界；`.github/workflows/ci.yml` — 将三个业务网络开关提升到工作流级，两个任务均继承；`docs/project-ledger.md` — 追加本条证据。所有项目文件都可经本次差异单独回退。依赖安装临时生成的未跟踪示例 `lefthook.yml` 与本次新装的 `.git/hooks/prepare-commit-msg` 已核对内容及创建时间后移除，未修改仓库原有跟踪文件。
- 验证 / Verification: `uv sync --locked --python 3.12` → 0；`ENABLE_TELEGRAM_NETWORK=0 ENABLE_TELEGRAM_ACCOUNT_NETWORK=0 ENABLE_TRON_NETWORK=0 uv run --no-sync python manage.py test botcore.tests` → 0，97 项通过；同环境下 `python manage.py check` → 0，0 项问题；`python manage.py makemigrations --check --dry-run` → 0、`No changes detected`；`pnpm install --frozen-lockfile` → 0、lockfile 未变；`pnpm --filter @vben/web-antd typecheck` → 0；`pnpm --filter @vben/web-antd build` → 0，保留既有 `%VITE_APP_TITLE%` 未定义警告；最终 `actionlint -color .github/workflows/ci.yml` → 0，`git diff --check` → 0。以上是 macOS 本地/静态证据，不是 Ubuntu runner、浏览器、真实 Telegram/TRON 或生产证据。
- 时间逻辑 / Time logic: 系统时钟 `Asia/Shanghai`，本条 UTC 对应 `2026-09-26T18:16:48Z`；GitHub 事件按平台处理，本工作流不解析时间、调度或重试业务操作。
- 利用 / Reuse: 后续将工作流提交并推送 `main` 后读取真实 GitHub run ID 与两个 job 的退出结果；若需网页手动触发，应先由仓库维护者决定让该工作流进入当前默认分支或调整默认分支。回退路径：删除本次新建 `.github/workflows/ci.yml` 与 `docs/project-ledger.md`，仅反向应用本次 README/CHANGELOG/版本记录增量；不触及业务状态或服务。
- 限制 / Limits: 未提交、未推送、未创建 PR，未在 GitHub 托管 runner 运行；默认分支为 `master` 时仅位于 `main` 的工作流没有可用的网页手动触发入口。前端本地验证使用当前 macOS Node v24，但 CI 配置读取仓库 `frontend/.node-version`（22.22.0）；该版本组合是否在 Ubuntu runner 上成功仍需真实运行确认。
- 下一步 / Next: 如用户要求发布，再执行有范围的提交/推送，并以新 run ID 和 job 日志验证远端 CI；不以本地绿灯替代远端验收。

## 2026-09-27T02:18:11+08:00 — 最终只读核验补充

- 状态 / Status: 完成（本地交付）；远端运行未运行。
- 读取 / Read: GitHub 仓库 Actions 权限 API 返回 `enabled=true`、`allowed_actions=all`；仅代表设置允许工作流，不代表产生 run。`pnpm --version` 在 `frontend/` 返回 `10.33.0`；仓库根目录全局 pnpm 为 `11.16.0`，本次前端命令均在 `frontend/` 内运行。
- 验证 / Verification: 最后执行 actionlint、`git diff --check`、Git 状态读取均退出码 0；待交付修改仍仅 `.github/workflows/ci.yml`、`README.md`、`CHANGELOG.md`、`docs/version-record.md`、`docs/project-ledger.md`。本条系统时钟 `Asia/Shanghai`，对应 UTC `2026-09-26T18:18:11Z`。
- 修改 / Write: `docs/project-ledger.md` — 仅追加远端设置和版本校验边界；可单独回退本条，不改变工作流或业务数据。
- 下一步 / Next: 保持本地修改供用户审核；提交或推送需另行要求。

## 2026-09-28 — 自托管 Runner 验收准备

- 状态 / Status: 进行中
- 读取 / Read: GitHub 仓库 `shiyi-log/bot` 元数据确认当前默认分支为 `master`、可见性为 private；仓库 Runner API 确认 `ci-runner-shiyi-bot` 与 `ci-runner-shiyi-2-bot` 均为 Linux x64、online、idle，并带有 `repo-bot` 标签；`.github/workflows/ci.yml` 当前两个任务原先使用 `ubuntu-latest`。
- 修改 / Write: `.github/workflows/ci.yml` — backend/frontend 两个任务改用 `[self-hosted, Linux, X64, repo-bot]`；同步修正文档中关于 Runner 类型与验收边界的说明。未加入密钥、真实网络调用或部署步骤。
- 验证 / Verification: 待推送 `main` 后读取真实 GitHub Actions run、job、Runner 分配状态及测试退出码；失败时仅修复仓库内逻辑或工作流配置，并重新触发验证。
- 限制 / Limits: 当前 shell 位于 macOS 工作区，无法直接读取远端 Runner 主机的 `svc.sh status`；GitHub API 可证明 Runner online/idle，但不能替代主机级资源健康检查。
- 下一步 / Next: 提交并推送 `main`，等待两个自托管任务完成，再按日志逐项验收。
