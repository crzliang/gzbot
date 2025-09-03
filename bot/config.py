"""
配置管理模块
"""
import os

# 读取环境变量中的数据库连接信息
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

# 允许触发命令的群聊 ID，逗号分隔；为空表示不限制
ALLOWED_GROUP_IDS_RAW = os.getenv("ALLOWED_GROUP_IDS", "")
ALLOWED_GROUP_IDS = set()
if ALLOWED_GROUP_IDS_RAW:
    try:
        ALLOWED_GROUP_IDS = set(int(x.strip()) for x in ALLOWED_GROUP_IDS_RAW.split(",") if x.strip())
    except Exception:
        ALLOWED_GROUP_IDS = set()

# 从 .env 文件读取要监听的比赛 ID
TARGET_GAME_ID = os.getenv("TARGET_GAME_ID")

# Category 数字到名称的映射
CATEGORY_MAPPING = {
    0: "Misc",
    1: "Crypto",
    2: "Pwn", 
    3: "Web",
    4: "Reverse",
    5: "Blockchain",
    6: "Forensics",
    7: "Hardware",
    8: "Mobile",
    9: "PPC",
    10: "AI",
    11: "Pentest",
    12: "OSINT"
}
