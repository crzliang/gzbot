# gzbot

本项目基于 NoneBot2 框架，集成 PostgreSQL 数据库，实现机器人自动或命令播报数据库内容。

## 功能说明
- 连接 PostgreSQL 数据库，读取指定内容
- 通过 NoneBot2 机器人进行播报（如定时播报或命令触发）

## 快速开始
1. 安装依赖
2. 配置数据库连接
3. 启动机器人

## 依赖
- nonebot2
- asyncpg
- nonebot-adapter-onebot

## 启动
```bash
nb run
```

## 配置
请在 .env 文件中配置数据库连接信息，例如：
```
POSTGRES_DSN=postgresql://user:password@localhost:5432/dbname
```

## 目录结构
- bot/         # 机器人插件目录
- .env         # 环境变量配置
- README.md    # 项目说明
