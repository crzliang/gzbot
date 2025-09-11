# gzctf-bot

基于 NoneBot2 + OneBot v11 + PostgreSQL 的赛事助手机器人，支持查询题目、排行榜，以及一血/二血/三血/公告/提示/新题目的自动播报（可开关）。

通过直接使用SQL语句查询数据库的数据，可通过这个方法绕过平台的验证码验证；**因此这项服务不推荐使用公网服务器进行部署**

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

## 本地部署运行

### 环境要求
- Python 3.11/3.12（已在 3.12 上验证）
- PostgreSQL 可访问实例

建议使用虚拟环境。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install nonebot2 nonebot-adapter-onebot asyncpg nonebot-plugin-apscheduler python-dotenv uvicorn
```

或者使用项目的 pyproject 进行安装（若使用 Poetry/现有锁定文件，请按需调整）。

### 配置
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

### 启动
项目内提供了 `app.py`，会加载 .env、注册 OneBot v11 适配器并启动服务。

```bash
source .venv/bin/activate
python app.py
```

OneBot v11 连接方式（例如 go-cqhttp）请按各自文档配置上报与反向 WS/HTTP（确保与本服务监听一致）。

## 使用 Docker 部署运行（推荐）

直接使用 GitHub Packages (ghcr.io) 发布的镜像。

### docker-compose 部署运行:

复制目录下的docker-compose-example.yml文件的内容到本地，重命名为docker-compose.yml，注意要**配置好环境变量**

我是使用napcat作为qq的客户端，所以在yml文件中也带上了napcat的配置。如果你习惯使用其他的客户端，请自行配置。

启动命令
```
docker compose up -d
```

### 本地构建后使用 Docker 部署运行
已提供 `Dockerfile`，构建（本地）：

```bash
docker build -t <自己命名镜像名> .
```
然后自行配置docker-compose.yml文件即可，可参考docker-compose-example.yml