# Telegram TRON Bot Template

可二次开发的 Telegram 机器人半成品模板。后端使用 Django 5.2 + Django REST Framework，前端基于 Vben Admin 5.7.0，内置欢迎消息、Telegram 用户/群组 ID 采集、Telegram 个人账号管理、TRON 地址只读监控和管理页面。

## 已实现

- 多机器人独立启停、欢迎文案与 URL 按钮配置
- 机器人可独立开启克隆权限；克隆复制安全配置和按钮，自动生成新的令牌环境变量名，并预留收费接口
- Telegram `/start`、`/id`、`/chatid`，首次私聊及新成员入群欢迎
- Telegram 用户与群组公开信息持久化、搜索、分页和列表展示
- 群组成员仅在群组内发言时采集，用户名和姓名随下一次发言动态更新
- TRON 地址合法性校验、TRX/TRC20 USDT 余额与最近交易轮询、逐地址错误隔离及单地址检查
- Vben 机器人、按钮、用户、群组、群组成员、TRON 地址和运行设置页面
- Vben Telegram 账号管理页：手机号、验证码、二级密码三步登录，续登、状态检查、搜索和本地删除
- 默认关闭 Telegram/TRON 真实网络访问，缺少显式开关或凭据时拒绝运行
- 项目专属技能：`skills/telegram-tron-bot/`

## 本地启动

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8010
```

另开终端：

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm --filter @vben/web-antd dev --host 127.0.0.1
```

访问 `http://127.0.0.1:5173/`。Vite 会把 `/api` 代理到 `http://127.0.0.1:8010`。

## 机器人与监控

复制 `.env.example` 为 `.env`，为每个机器人填写其后台配置的令牌环境变量。TRON API Key 可直接在“运行设置”中录入明文，或仅配置环境变量名作为兜底；页面和接口只显示脱敏预览，日志与提交内容不会包含 Key。真实网络功能仍需后台启用机器人并显式开启环境变量：

```bash
ENABLE_TELEGRAM_NETWORK=1 uv run python manage.py run_bot
ENABLE_TELEGRAM_NETWORK=1 uv run python manage.py run_bot --bot-id 2
ENABLE_TRON_NETWORK=1 uv run python manage.py monitor_tron
```

个人 Telegram 账号登录需要另外配置 `TELEGRAM_API_ID`、`TELEGRAM_API_HASH` 或运行设置中的对应值，并显式开启 `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1`。账号会话、验证码哈希和 API Hash 使用 `CONFIG_ENCRYPTION_KEY`（未配置时从 Django `SECRET_KEY` 派生）加密保存；接口只返回公开身份、状态和脱敏预览，不返回会话、验证码或 Hash 原值。测试不会连接 Telegram 网络。

`run_bot` 默认并发运行全部已启用且凭据已配置的机器人，`--bot-id` 可重复指定多个机器人；两个命令均支持 `--once`。TRON API 地址、明文 API Key 和 API Key 环境变量名可在“运行设置”配置；Key 支持换行、逗号或分号分隔并在 401 时轮换，数据库值优先于环境变量。按钮为 URL 类型的 Telegram 内联键盘，仅随 `/start`、首次私聊欢迎和新成员欢迎发送。TRON 功能仅进行只读查询，不包含私钥、签名、转账或支付执行。

机器人列表的“克隆”操作只复制欢迎配置和按钮，克隆结果默认停用且必须单独配置 Telegram 令牌环境变量。`POST /api/bots/{id}/clone/` 已预留 `billing_plan` 字段和计费状态返回，当前不执行收费或支付。

## 验证

```bash
uv run python manage.py test botcore.tests
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
cd frontend
pnpm --filter @vben/web-antd typecheck
pnpm --filter @vben/web-antd build
```

接口契约见 `docs/backend-api.md`。群组成员采集只处理群组或超级群组中的普通内容消息；入群事件、私聊、频道消息和匿名管理员消息不会创建成员记录。当前前端使用本地开放身份、API 使用 `AllowAny` 以便模板直接运行；部署生产环境前必须同时替换为正式认证与权限策略。
