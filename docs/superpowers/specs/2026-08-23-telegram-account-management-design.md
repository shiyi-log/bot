# Telegram 账号管理设计

日期：2026-08-23

## 目标

在现有 Vben 管理端加入 Telegram 客户端账号管理，并通过 Telethon 实现真实的手机号、验证码、二级密码三步登录。账号管理与 Bot API 机器人管理保持独立，本期只提供登录、续登、状态检查和删除，不自动监听、采集或发送消息。

## 架构

- Django 新增独立的 `TelegramLoginAccount` 模型，保存账号公开资料、登录状态和加密登录材料。
- Django 新增 Telegram 账号登录服务，封装手机号规范化、Telethon 客户端、超时、异常转换和会话检查。
- Vben 新增“Telegram 账号”菜单页，使用三步弹窗完成登录，并支持从未完成状态继续。
- 现有“运行设置”页新增 Telegram API 配置区，数据库配置优先，环境变量作为兜底。
- Telegram 账号登录网络使用独立开关 `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1`，默认关闭，不复用 Bot API 轮询开关。

## 数据模型

`TelegramLoginAccount` 包含：

- `label`：账号显示名称。
- `phone`：国际格式手机号。
- `telegram_id`：Telegram 64 位用户 ID。
- `username`、`first_name`、`last_name`：登录后读取的公开身份字段。
- `status`：`pending`、`code_sent`、`password_required`、`logged_in`、`session_expired` 或 `error`。
- `phone_code_hash`：加密的验证码请求哈希。
- `session_string`：加密的 Telethon StringSession，登录中和登录后复用。
- `last_error`：截断后的非敏感错误摘要。
- `last_checked_at`、`created_at`、`updated_at`：状态时间。

`BotSettings` 增加 Telegram API ID 和 API Hash 配置。API ID 可回显；API Hash 加密存储且仅接受写入，响应只返回是否配置和脱敏预览。

敏感值使用 Fernet 加密。密钥优先读取 `CONFIG_ENCRYPTION_KEY`，未配置时从 Django `SECRET_KEY` 派生。API Hash、验证码哈希、会话串、验证码和二级密码不得出现在 API 响应、日志、测试夹具或 Git 中。

## API 契约

- `GET /api/telegram-accounts/`：分页查询账号。
- `DELETE /api/telegram-accounts/{id}/`：删除本地账号记录和加密会话，不调用 Telegram 注销其他设备。
- `POST /api/telegram-accounts/login/start/`：校验国际手机号、发送验证码并返回账号及下一步。
- `POST /api/telegram-accounts/login/code/`：提交验证码；成功或进入二级密码步骤。
- `POST /api/telegram-accounts/login/password/`：提交二级密码并完成登录。
- `POST /api/telegram-accounts/{id}/check/`：检查会话是否仍有效并刷新公开资料。
- `GET /api/settings/`、`PATCH /api/settings/`：同步读写 Telegram API 配置状态。

所有账号响应只包含公开字段、状态、`has_session` 和时间字段。登录接口在网络开关关闭、凭据未配置或状态不匹配时拒绝执行。

## 登录流程

1. 前端提交国际格式手机号。
2. 后端检查网络开关与 API 凭据，通过 Telethon 发送验证码，保存加密验证码哈希和临时会话，将状态改为 `code_sent`。
3. 前端提交验证码。无需二级密码时完成登录；Telegram 要求二级密码时保存更新后的加密会话，将状态改为 `password_required`。
4. 前端提交二级密码，后端完成登录并从 `get_me()` 更新公开身份字段，将状态改为 `logged_in`。
5. 页面关闭或刷新后，`code_sent` 和 `password_required` 账号可从对应步骤继续；也可重新发送验证码。
6. 状态检查发现未授权会话时改为 `session_expired`，允许重新登录。

## 前端设计

- 页面顶部显示 Telegram API 凭据状态、网络开关说明、“登录账号”和“刷新”操作。
- 表格展示账号名称、手机号、Telegram 用户 ID、用户名、姓名、状态、最近检查时间和更新时间。
- 行操作包括继续登录或重新登录、状态检查、删除。
- 登录弹窗使用手机号、验证码、二级密码三步 Steps；验证码步骤提供“重新发送验证码”，所有提交防止重复点击。
- 设置页的 API Hash 输入框保存后清空，仅展示脱敏预览和配置状态。
- 删除使用二次确认，明确只删除本地记录。

## 错误处理

- 手机号必须使用 `+` 和国家码，拒绝本地格式和无效长度。
- Telethon 操作使用有限超时，超时提示检查 Telegram 网络或代理。
- 验证码错误、验证码过期、Flood Wait、二级密码错误、凭据缺失和会话失效转换为稳定中文错误。
- `last_error` 只保存截断后的错误摘要，不保存验证码、二级密码、API Hash 或会话。
- 登录失败保留可安全重试的状态；无法继续的会话标记为 `error` 或 `session_expired`。

## 测试与验收

- 后端测试全部注入假 Telethon 传输，不进行真实 Telegram 网络请求。
- 覆盖网络默认关闭、配置缺失、发送验证码、无二级密码登录、二级密码登录、续登、重新发送、会话检查、错误脱敏和删除。
- 验证所有 API 响应不包含 API Hash、验证码哈希、会话、验证码或二级密码。
- 运行 Django 测试、系统检查和迁移漂移检查。
- 运行 Vben 类型检查和生产构建。
- 真实验证码仅由操作者显式配置凭据并开启 `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1` 后手工验证，自动测试不触发。

## 非目标

- 不实现个人号自动监听、群组成员采集、消息发送或历史消息同步。
- 不实现 Telegram 设备列表管理或远端会话注销。
- 不把账号会话导出到前端或提供下载接口。
- 不修改现有 Bot API 机器人轮询和 TRON 只读监控边界。
