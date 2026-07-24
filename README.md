# Distributed Bot Manager

基于 Django、Redis 和异步任务的 Telegram 多机器人管理服务，可由工作节点领取配置、上报心跳并运行机器人实例。

## 组件

- `manage.py`：Django 管理入口。
- `run.py`：机器人调度进程。
- `worker.py`：工作节点同步与心跳进程。
- `bots/`、`core/`：数据模型和运行逻辑。

## 启动顺序

准备 Python 环境、MySQL/Redis 和项目配置后，先执行 Django 迁移并启动管理服务，再运行 `python run.py` 或 `python worker.py`。

仓库当前未提供依赖锁定文件。部署前应补充依赖清单，并将 Bot Token、数据库密码、Redis 密码和服务地址迁移到环境变量。

## 系统如何工作

Django 中的 `Worker`、`Bot`、`BotConfig`、`BotUser` 和键盘模型保存节点、机器人及交互配置。工作节点通过 HTTP 注册并周期上报心跳，服务端按在线状态分配 Bot；`worker.py` 拉取本节点分配结果并通知运行进程。`core/bot_runner.py` 将数据库 Token 同步到 Redis，按差异启动或停止 aiogram Bot。消息中间件记录用户并把消息转发给创建者，键盘配置被缓存到 Redis，通过订阅刷新，避免每条消息查询数据库。调度器会重新分配离线节点上的 Bot。
