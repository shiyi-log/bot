# 版本记录

## 2026-09-29 — 公开发布

仓库已切换为公开可见，默认分支设为 `main`，仓库描述和根目录 MIT License 已补齐。公开仓库的 GitHub Actions 使用 `ubuntu-latest`，并移除原先登记的长期自托管 Runner，避免外部 Pull Request 执行在受信任主机上。

公开前使用 `git-filter-repo` 从 `main`、`master`、`anniu` 可达历史移除 `bot_manager.log` 和 `django_server.log`；全历史 Telegram Bot Token、常见私钥/平台密钥模式扫描为 0 命中，`git fsck --full --no-reflogs --unreachable` 无不可达对象。清理前 bundle 备份保存在本机 `/Users/a399/Desktop/data/bot-pre-public-20260929.bundle`，不属于仓库内容。

GitHub 托管 CI 的一次触发曾因账号支付状态被 GitHub 拒绝启动；代码公开不依赖该次运行结论，需在账户计费恢复后重新检查工作流。

## 未发布 — 离线 CI

新增 `.github/workflows/ci.yml`，将现有 Django `botcore.tests`、系统检查、迁移漂移检查与 Vben 类型检查、构建分为两个独立的 GitHub Actions 任务，并使用 GitHub 托管的 `ubuntu-latest` Runner。Python、Node 和 pnpm 版本明确指定，依赖按锁文件安装；工作流权限只读，Telegram/TRON 业务网络开关显式关闭，不要求密钥，也不部署服务。

前端任务先安装 Node，再安装 pnpm，并在冻结依赖安装时显式把 `PNPM_HOME` 注入 PATH，兼容 workspace 递归 postinstall 脚本。本地对工作流运行 actionlint 静态校验，执行 97 项 Django 测试、系统检查、迁移漂移检查、Vben 类型检查与生产构建。构建保留既有 `%VITE_APP_TITLE%` 未定义警告；公开仓库改用 GitHub 托管 Runner，避免不受信任 PR 接触长期自托管主机。

## v0.5.1 - 2026-09-13

新增 `scripts/start-dev.sh` 一键开发启动入口。脚本自动执行 Django 数据库迁移，同时启动后端和 Vben 前端；默认地址为 `127.0.0.1:8010` 与 `127.0.0.1:5173`。启动前检查端口占用，避免终止已有服务；支持 `BACKEND_HOST`、`BACKEND_PORT`、`FRONTEND_HOST`、`FRONTEND_PORT` 覆盖。Ctrl-C 仅停止本次脚本启动的进程。

验证：完成 `bash -n scripts/start-dev.sh` 静态语法检查，并使用临时端口执行启动冒烟测试。

## v0.5.0 - 2026-09-13

新增独立 TRON 扫块器。扫块器使用 TRONGrid `getnowblock`/`getblockbynum` 读取确认区块，维护数据库游标，解析 TRX `TransferContract` 与 USDT `transfer` 调用，并按交易 ID与合约索引幂等保存命中启用监控地址的事件。支持 `--once`、`--confirmations`、`--batch-size`，网络开关关闭时 fail-closed；未执行真实链上请求。

## v0.4.1 - 2026-08-30

迁入 Shop 地址监控的账户快照逻辑：TRONGrid 账户查询同时解析 TRX 与 USDT（最小单位），保留 API Key 轮换和逐地址错误隔离。新增 `POST /api/tron/addresses/{id}/check/` 单地址只读检查，仍要求 `ENABLE_TRON_NETWORK=1` 与有效凭据；未执行真实链上请求。

## v0.4.0 - 2026-08-24

完成 Telegram 客户端账号管理。新增 `TelegramLoginAccount`、加密会话与验证码哈希、手机号唯一迁移清理，以及真实 Telethon 三步登录接口。账号资料接口为只读集合，通用 POST/PATCH 返回 405；账号搜索覆盖手机号、Telegram ID、用户名、姓名和备注。

运行设置新增 `telegram_api_id`、`telegram_api_hash`、`telegram_api_hash_configured` 和 `telegram_api_hash_preview`。API Hash、验证码哈希和 Telethon session 使用 Fernet 加密，原值不会通过响应返回。`ENABLE_TELEGRAM_ACCOUNT_NETWORK=1` 是真实个人账号网络调用的独立开关，测试全部使用假 Telethon 客户端；本轮未发送真实验证码。

验证：Django 后端测试、迁移测试、系统检查和迁移漂移检查通过；Vben typecheck、oxlint 和生产构建通过。构建仍有既有 `%VITE_APP_TITLE%` 环境变量警告。

## v0.3.4 - 2026-08-23

新增机器人级 `clone_enabled` 权限与 `POST /api/bots/{id}/clone/`。仅允许克隆已开放权限的机器人；克隆只复制欢迎消息配置和按钮，不复制 Telegram ID、用户名、启用状态或令牌信息，并自动生成唯一令牌环境变量名。接口接受可选 `billing_plan`，返回预留的 `billing` 状态，但当前模板不接入收费、支付或订单执行。

## v0.3.3 - 2026-08-18

修复全页面截图检查发现的前端问题。运行设置页改用单一 API Key 双向绑定，消除 Ant Design Vue 的监听器类型警告，并将提示文字更新为当前明文存储、脱敏回显和环境变量兜底规则。顶部标签默认最多保留 5 个；用户、群组、成员、机器人、按钮和 TRON 地址表格固定首列并启用粘性横向滚动条，提升窄窗口下的浏览效率。

## v0.3.2 - 2026-08-17

按用户要求取消 TRON API Key 加密。`BotSettings.tron_api_key` 以明文保存，PATCH 可写入，GET/响应只返回 `tron_api_key_preview` 脱敏值；未填写数据库 Key 时才读取 `tron_api_key_env_var` 指定的环境变量。支持多 Key 分隔配置和 HTTP 401 轮换，仍保持默认关闭与只读监控。数据库及备份必须按生产密钥处理。

## v0.3.1 - 2026-08-17

补全 TRON 运行设置。管理员现在可以配置 TRON API 地址和 API Key 环境变量名，并查看服务端环境变量是否已配置；API Key 本身不会通过页面提交、数据库保存或 API 返回。监控命令按设置读取 API 地址和环境变量，仍保持只读与默认关闭。

验证范围包括 Django 离线 API 测试、系统检查、迁移漂移检查和 Vben 类型检查；未执行真实 TRONGrid 请求。

## v0.3.0 - 2026-08-15

打通多机器人与按钮设置。后端新增机器人、机器人用户关系和 URL 按钮模型；每个机器人独立配置启用状态、欢迎文案、令牌环境变量名和按钮布局，令牌值始终只从运行环境读取。`run_bot` 默认并发运行全部符合条件的机器人，也支持重复使用 `--bot-id` 精确选择。

Telegram 首次私聊欢迎改为按机器人判断，群组发言成员也带机器人来源，同一用户可被不同机器人分别记录；群组汇总仍按不同用户去重。旧全局机器人设置和已有成员、用户数据通过迁移归入默认机器人。Vben 新增机器人管理、按钮设置页面，并在群组成员页加入机器人筛选；原设置页仅保留 TRON 只读监控配置。

验证范围包括 20 个 Django 离线测试、系统检查、迁移升级与漂移检查，以及 Vben 类型检查、lint 和生产构建。真实 Telegram 与 TRON 网络保持关闭，未执行外部发送或链上请求。

## v0.2.0 - 2026-08-15

新增群组发言成员采集。后端增加群组成员模型、迁移和只读查询接口，并在群组列表返回已发言成员数。成员仅在群组或超级群组发送普通内容消息时创建或更新；入群、私聊、频道、纯服务事件和匿名管理员消息不会入表。用户名与姓名快照会在成员下一次群组发言时刷新，同时累计发言次数。

前端增加“群组成员”页面，支持按群组筛选、关键词搜索、分页、刷新，以及从群组列表直接查看成员。验证范围包括 Django 离线测试、系统检查、迁移漂移检查、Vben 类型检查与生产构建；真实 Telegram 网络仍保持关闭且未执行。

## v0.1.0 - 2026-08-15

首个可运行半成品版本。后端提供 Telegram 用户、群组、设置与 TRON 地址 REST API；机器人运行时支持欢迎消息及 ID 查询；TRON 运行时提供只读余额和最近交易轮询。前端基于 Shop 使用的 Vben 5.7.0 基线完成四个管理页面。

验证范围：Django 离线单元测试、系统检查、迁移漂移检查、Vben 类型检查和生产构建。未执行真实 Telegram 长轮询或 TRONGrid 请求；为方便模板直接运行，当前采用本地开放身份和 `AllowAny`，生产认证尚未接入。
