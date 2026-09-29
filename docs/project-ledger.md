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

## 2026-09-28 — 首次自托管 Run 结果与前端安装修复

- 状态 / Status: 进行中
- 读取 / Read: Actions run `36437350315`（commit `7ea3bdd`）及两个 job 结果；Django job `108978587027` 在自托管 Runner 上完成 97 项测试、系统检查和迁移漂移检查；Vben job `108978586876` 在 `pnpm/action-setup` 失败，GitHub 注释为 `self-installer exits with code 127`，其后的 Node、依赖、typecheck 和 build 未执行。
- 判断 / Diagnosis: 该失败发生在 Runner 环境适配层，不是应用逻辑。自托管 Runner 不能假设 GitHub 托管镜像已预装可供 `pnpm/action-setup` 自安装器调用的 Node；原工作流先装 pnpm、后装 Node，导致 pnpm 自安装器找不到运行时。
- 修改 / Write: `.github/workflows/ci.yml` — 前端任务改为先运行锁定 Node 22.22.0 的 `actions/setup-node`，再运行锁定 pnpm 10.33.0 的 `pnpm/action-setup`；移除 setup-node 的 pnpm cache 参数，避免在 pnpm 安装前读取不存在的命令。未改变测试命令、依赖锁定或网络开关。
- 验证 / Verification: 首次远端 run 的 backend 已通过；前端修复待新提交触发第二次自托管 run。
- 限制 / Limits: 当前 shell 无法直接读取 Runner 主机的 `svc.sh status`；GitHub API 仍能证明 Runner online/idle 与 job 分配。
- 下一步 / Next: 提交并推送前端安装顺序修复，等待第二次 run 完成。

## 2026-09-28 — 第二次自托管 Run 结果与递归 pnpm PATH 修复

- 状态 / Status: 进行中
- 读取 / Read: Actions run `36438581863`（commit `19a7600`）及失败 job `108982811928` 的完整日志；Node 与 pnpm 安装成功，依赖下载及多数 workspace postinstall 已完成，最后 `scripts/vsh` 的递归脚本报 `sh: 1: pnpm: not found`，随后 `ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL`。
- 判断 / Diagnosis: 失败仍在前端 Runner/安装环境层，不是应用逻辑或锁文件漂移。`pnpm/action-setup` 暴露了 `PNPM_HOME`，顶层 pnpm 可执行，但递归生命周期脚本未继承该目录到 PATH。
- 修改 / Write: `.github/workflows/ci.yml` — `pnpm install --frozen-lockfile` 改为先显式 `export PATH="${PNPM_HOME}:${PNPM_HOME}/bin:${PATH}"` 并用 `command -v pnpm` 记录解析路径，再执行同一冻结安装命令。测试、构建、依赖版本和网络开关不变。
- 验证 / Verification: 第二次 run 的 backend 已通过；前端 PATH 修复待第三次自托管 run 验证。
- 限制 / Limits: 当前 shell 无法直接读取 Runner 主机的 `svc.sh status`；Runner API 与 Actions job 已证明分配到 `ci-runner-shiyi-bot` 且保持 online。
- 下一步 / Next: 提交并推送递归脚本 PATH 修复，等待第三次 run 完成。

## 2026-09-28 — 开源公开化准备

- 状态 / Status: 进行中
- 读取 / Read: GitHub 仓库仍为 private，默认分支为 `master`；历史安全扫描发现 `bot_manager.log` 与 `django_server.log` 的旧提交包含 Telegram Bot API Token 和运行日志。当前工作树不含这些日志，但远端历史仍可访问。
- 修改 / Write: `.github/workflows/ci.yml` — 两个任务改回 GitHub 托管 `ubuntu-latest`，避免公开仓库的外部 PR 使用长期自托管 Runner。`README.md` — 增加开源许可证与凭据安全说明，并同步 CI 边界。`LICENSE` — 新增根目录 MIT License。`CHANGELOG.md`、`docs/version-record.md` — 记录公开化准备和历史凭据清理范围。
- 验证 / Verification: 待创建可恢复 bundle 备份后，重写 `main`、`master`、`anniu` 的历史并移除两份日志；重写后扫描所有分支和对象中的 Telegram Token 模式，再强制推送。
- 限制 / Limits: 不能把当前仓库声明为已安全公开，直到历史重写、远端 refs 更新和 GitHub 可见性核验全部完成。
- 下一步 / Next: 备份、历史清理、全历史扫描、推送并切换默认分支/公开可见性。

## 2026-09-29 — 公开发布完成

- 状态 / Status: 完成（公开仓库）；GitHub 仓库 `shiyi-log/bot` 已为 public，默认分支为 `main`，仓库许可证识别为 MIT。
- 读取 / Read: GitHub API 核对 public 可见性、`main` 默认分支、根目录许可证、Actions Runner 数量和 Secret Scanning 设置；远端分支 `main`、`master`、`anniu` 已全部接收重写后的提交。
- 修改 / Write: 使用 `git-filter-repo --invert-paths --path bot_manager.log --path django_server.log` 重写并强制推送三个远端分支；删除仓库登记的两个自托管 Runner；工作流改为 `ubuntu-latest`；补充根目录 `LICENSE`、README 开源与安全说明、版本记录。
- 验证 / Verification: 清理前 bundle `/Users/a399/Desktop/data/bot-pre-public-20260929.bundle` 可恢复；重写后 `git rev-list --all --objects` 不含两份日志，所有可达提交 Telegram Token/常见私钥与平台密钥扫描为 0 命中，`git fsck --full --no-reflogs --unreachable` 无不可达对象；GitHub API 显示 Runner 数量为 0。公开切换后的 CI run `36450037749` 未启动，GitHub 返回账户支付失败或 spending limit 限制，非代码失败。
- 限制 / Limits: 历史中曾存在的 Telegram Token 已按用户授权从 Git 历史移除，但相关 BotFather Token 仍应确认已撤销/轮换；CI 验证范围仍是离线逻辑与构建，不包含真实 Telegram/TRON 网络。
- 下一步 / Next: 继续保持所有真实 Telegram/TRON 网络开关默认关闭，并在后续依赖或业务变更后复用同一 CI 门禁。

## 2026-09-29 — GitHub CI 公开仓库验收通过

- 状态 / Status: 完成
- 读取 / Read: Actions run `36450888753`（commit `5fc2b0b3b33247221eef384316a1a0b4a2c18b29`）及两个 job 的完整步骤状态；GitHub API 显示 run conclusion 为 `success`。
- 验证 / Verification: `Django offline checks` job 成功执行 `uv sync --locked`、97 项 `botcore.tests`、`manage.py check` 与 `makemigrations --check --dry-run`；`Vben typecheck and build` job 成功执行 Node 22.22.0、pnpm 10.33.0、冻结依赖安装、`vue-tsc --noEmit --skipLibCheck` 和生产构建（`built in 5.94s`）。工作流级 Telegram Bot、Telegram account、TRON 网络开关均为 `0`，无真实外部网络验收。
- 结果 / Result: 当前 CI 逻辑在 GitHub 托管 Runner 上有真实绿灯证据；此前支付状态导致的未启动 run 不再是当前阻塞。

## 2026-09-29T13:38:00+08:00 — 重装系统前的代码与恢复资料基线

- 状态 / Status: 进行中；对应 UTC `2026-09-29T05:38:00Z`，时钟为本机 `Asia/Shanghai`（UTC+08:00）。
- 目标 / Goal: 核对并推送本仓库、留下离线 Git 恢复点和重装后的最小恢复步骤；不把本机密钥、会话、数据库或配置提交到公开仓库，也不执行系统抹盘。
- 基线 / Baseline: 本仓库的 `main` 为 `4f8bf71f73ea2f64b9ff290d238d48a6ea689a75`；开始时工作树干净，`git fetch --prune origin`、`git ls-remote --heads origin` 证实 `main`、`anniu`、`master` 均与远端一致；`git push origin main` 返回 `Everything up-to-date`。本机另有被忽略的零字节 `db.sqlite3`、`.venv/`、`frontend/node_modules/`；根目录 `.env` 不存在。无外接备份卷，Time Machine 未配置目的地。
- 读取 / Read: `README.md`、`docs/backend-api.md`、`skills/telegram-tron-bot/SKILL.md`、`AGENTS.md` — 项目结构、只读/默认断网边界与文档要求；`CHANGELOG.md`、`docs/version-record.md`、`docs/project-ledger.md` — 现有记录；`.gitignore`、`.env.example`、`config/settings.py` — 受忽略文件、配置来源、SQLite 和加密密钥依赖；`pyproject.toml`、`frontend/.node-version`、`frontend/package.json`、`scripts/start-dev.sh` — Python/Node/pnpm 版本和重建命令；`git status`、分支/远端引用、忽略文件元数据、`tmutil`、`/Volumes` — 当前恢复边界。敏感配置只读取元数据/路径，未输出原值。
- 范围 / Scope: 写入简短的公开仓库恢复指南、README 入口、变更/版本记录和本台账；生成仓库外 Git bundle、校验和及本机清单。既有源码/API、真实 Telegram/TRON、系统配置、凭据和其他目录均不修改。
- 修改 / Write: 仓库外 `bot-pre-reinstall-20260929.bundle` — `git bundle create --all` 创建完整历史备份，可删除本次生成文件回退；相邻 `.sha256` 和 `-manifest.txt` — 只记录散列、引用及需单独保管的本机路径，不记录凭据原值；`docs/project-ledger.md` — 追加本条基线，可用新提交回退本次增量。完成文档/提交后将重新生成并验证最终 bundle 与清单。
- 验证 / Verification: `git bundle verify` → 0，包含 `main`、`anniu`、`master` 等 8 个引用及完整历史；初始 SHA-256 `88b8600c0c6c0ba221d8e320e3667fc0b69c949415ffa5982086f3610d492594`。`git fsck --full --no-reflogs --unreachable` → 0、无输出；`git diff --check` → 0。以上是本机和远端 Git 证据，不是异机备份或业务运行验收。
- 时间逻辑 / Time logic: 仅以系统时钟/显式 UTC 偏移记录备份顺序，不解析业务时间；无调度、重试、过期或夏令时边界，重装前需再次确认最新提交和备份校验。
- 利用 / Reuse: GitHub 是代码主恢复源，bundle 是离线备份；被忽略文件和机密需用户在加密外部介质单独保管。旧的公开化前 bundle 含曾被清理的历史日志，不应上传公开网盘或并入新仓库。
- 限制 / Limits: 当前所有备份文件仍位于待重装电脑，不能视为抗抹盘备份；没有验证外部副本。同级其他项目的只读状态扫描发现多个工作树有未提交变更，另有一个项目领先远端 3 个提交；这些项目不属于本次提交范围，未对其执行写入或推送。尚未执行新文档的提交/推送或 CI。
- 下一步 / Next: 完成恢复指南与版本记录，验证后提交推送，再重建最终 bundle/散列并提醒用户做异机复制与核对。

## 2026-09-29T13:49:00+08:00 — 恢复指南与离线验证

- 状态 / Status: 进行中；对应 UTC `2026-09-29T05:49:00Z`，时钟为本机 `Asia/Shanghai`（UTC+08:00）。
- 目标 / Goal: 公开记录本仓库代码与本地环境的恢复边界，不公开本机凭据、私钥或其他项目细节。
- 读取 / Read: `config/settings.py`、`botcore/crypto.py` 和测试 — `CONFIG_ENCRYPTION_KEY` 缺失时使用 `SECRET_KEY` 派生 Fernet 密钥，旧数据库恢复依赖原密钥；`frontend/.node-version`、`frontend/package.json`、`pyproject.toml`、`scripts/start-dev.sh` — Node/pnpm/Python 要求、默认端口和启动即迁移行为；`.github/workflows/ci.yml` — 三个真实网络开关在离线 CI 中均关闭；`git diff`、`git status` — 改动仅为本次文档。
- 修改 / Write: `docs/reinstall-recovery.md` — 新建恢复指南，区分代码、数据库、密钥和整机备份，规定独立介质校验、恢复顺序与离线验证；`README.md` — 加入指南入口；`CHANGELOG.md`、`docs/version-record.md` — 记录本次可见文档变更；`docs/project-ledger.md` — 补充写入与验证证据；仓库外本机 `-manifest.txt` — 追加其他项目只读状态和敏感路径提醒。上述文档可通过反向应用本次提交回退；仓库外清单可单独更新/归档，未复制凭据原值。
- 验证 / Verification: `ENABLE_TELEGRAM_NETWORK=0 ENABLE_TELEGRAM_ACCOUNT_NETWORK=0 ENABLE_TRON_NETWORK=0 uv run --no-sync python manage.py test botcore.tests` → 0，104 项离线测试通过；相同环境下 `python manage.py check` → 0，零问题；`makemigrations --check --dry-run` → 0，无模型变化；`bash -n scripts/start-dev.sh` → 0；`git diff --check` → 0；所有指南引用的仓库文件/锁文件存在。未运行真实 Telegram/TRON、前端构建、生产或数据恢复验收。
- 时间逻辑 / Time logic: 文档只规定备份与恢复顺序，不实现时间解析；备份日期按 `Asia/Shanghai` 明确偏移，跨设备以 SHA-256 和 Git commit/ref 校验而非文件修改时间判断版本。
- 利用 / Reuse: 重装时从公开仓库克隆并按指南安装锁定依赖；若远端不可用，可使用最终 Git bundle，但被忽略数据和机密必须单独从安全备份恢复。文档回退不恢复被抹盘的数据。
- 限制 / Limits: GitHub 推送、CI 和外部介质复制尚待完成；清单与 bundle 仍留在待重装电脑，尚无整机备份。其他项目存在未提交/未推送状态，本任务未改动它们。
- 下一步 / Next: 提交推送本文档，重建最终 Git bundle 并校验；抹盘前由用户把所有需要的资料备份到独立介质并验证。
