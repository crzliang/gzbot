# gzbot

基于 NoneBot2 + OneBot v11 + PostgreSQL 的赛事助手机器人，支持查询题目、排行榜，以及一血/二血/三血/公告/提示/新题目的自动播报（可开关）。

## 功能
- 指令查询
	- /help 帮助
	- /gc 或 /gamechallenges 查询题目列表
	- /rank 查询总排行榜
	- /rank-XX 查询指定年级（两位数字前缀，如 25 表示 2025）的排行榜
- 自动播报（默认关闭，需要管理员开启）
	- 一血、二血、三血
	- 新题目开放、提示更新、公告
	- 开关命令：/open、/close

## 环境要求
- Python 3.11/3.12（已在 3.12 上验证）
- PostgreSQL 可访问实例

## 安装
建议使用虚拟环境。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install nonebot2 nonebot-adapter-onebot asyncpg nonebot-plugin-apscheduler python-dotenv uvicorn
```

或者使用项目的 pyproject 进行安装（若使用 Poetry/现有锁定文件，请按需调整）。

## 配置
在项目根目录创建 .env 文件，示例：

```
# 数据库连接串
POSTGRES_DSN=postgresql://user:password@host:5432/dbname

# 目标比赛 ID（必填）
TARGET_GAME_ID=1

# 允许触发命令的群号（可选，逗号分隔；留空表示不限制）
ALLOWED_GROUP_IDS=123456789,987654321

# 管理员 QQ 号（可选，逗号分隔；留空表示不限制）
ADMIN_QQ_IDS=111111,222222

# Web 监听（可选）
NB_HOST=0.0.0.0
NB_PORT=8080
```

说明：
- 自动播报默认关闭。管理员通过 /open 开启后，会以“开启指令时刻”为水位线，只播报之后产生的新通知，避免历史回放；/close 关闭。
- 排行榜学号前缀命令仅支持两位数字（正则限制为 \d{2}）。

## 启动
项目内提供了 `app.py`，会加载 .env、注册 OneBot v11 适配器并启动服务。

```bash
source .venv/bin/activate
python app.py
```

OneBot v11 连接方式（例如 go-cqhttp）请按各自文档配置上报与反向 WS/HTTP（确保与本服务监听一致）。

### 使用 Docker 运行
已提供 `Dockerfile`，也可直接使用 GitHub Packages (ghcr.io) 发布的镜像。

构建（本地）：
```bash
docker build -t ghcr.io/<owner>/<repo>:dev .
```

运行：
```bash
docker run --rm -p 8080:8080 \
	-e POSTGRES_DSN=postgresql://user:pass@host:5432/db \
	-e TARGET_GAME_ID=1 \
	-e ALLOWED_GROUP_IDS=123456 \
	-e ADMIN_QQ_IDS=111111 \
	ghcr.io/<owner>/<repo>:dev
```

GitHub Actions 会在推送到 master 时自动构建并推送镜像到 ghcr.io，镜像名为 `ghcr.io/<owner>/<repo>:<tag>`。

## 常用指令
- /help
- /gc 或 /gamechallenges
- /rank
- /rank-XX（示例：/rank-25）
- /open（管理员）
- /close（管理员）

## 开发说明
主要代码位置：
- `bot/commands.py` 指令处理
- `bot/database.py` 数据访问（asyncpg）
- `bot/utils.py` 格式化与通用工具
- `bot/notifications.py` 自动播报与调度（APScheduler）
- `bot/config.py` 配置项读取

依赖配置（节选）见 `pyproject.toml`：
- nonebot2
- nonebot-adapter-onebot
- asyncpg
- nonebot-plugin-apscheduler

## 故障排查
- 启动时报环境变量缺失：检查 `.env` 中的 `POSTGRES_DSN`、`TARGET_GAME_ID` 是否设置。
- 机器人无响应：确认 OneBot v11 适配器连接正常、群号是否在 `ALLOWED_GROUP_IDS` 中、命令前缀是否匹配。
- 自动播报未生效：自动播报默认关闭，请先用 `/open`；若仍无效，检查数据库是否真的有新通知产生（按 UTC 时间写入），以及应用日志。
- 数据库查询异常：核对 DSN、数据库权限、目标表结构；查看 `bot/database.py` 的 SQL 是否与实际表一致。

## 目录结构
```
bot/
	__init__.py
	commands.py
	config.py
	database.py
	notifications.py
	utils.py
app.py
pyproject.toml
README.md
.env (本地自建)
```

## 许可证
仅供内部/教学用途，按需自定。
