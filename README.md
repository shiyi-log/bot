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
