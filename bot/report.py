import asyncpg
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent
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

# 定义命令触发
report = on_command("report", priority=5)
gamechallenges = on_command("gamechallenges", aliases={"gc"}, priority=5)

@report.handle()
async def handle_report(bot: Bot, event: Event):
    # 限制：如果设置了 ALLOWED_GROUP_IDS，则仅允许来自这些群的 GroupMessageEvent
    if ALLOWED_GROUP_IDS:
        if not isinstance(event, GroupMessageEvent) or getattr(event, "group_id", None) not in ALLOWED_GROUP_IDS:
            await report.finish("此命令仅在指定群聊内可用。")

    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        # 示例查询，替换为你的表和字段
        rows = await conn.fetch("SELECT content FROM broadcast ORDER BY id DESC LIMIT 1")
        await conn.close()
        if rows:
            msg = rows[0]["content"]
        else:
            msg = "数据库暂无播报内容。"
    except Exception as e:
        msg = f"数据库读取失败: {e}"
    try:
        await bot.send(event, msg)
    except Exception as e:
        # 记录发送失败，便于排错
        print(f"DEBUG: Failed to send message in report: {e}")
        raise

@gamechallenges.handle()
async def handle_gc(bot: Bot, event: Event):
    print(f"DEBUG: gamechallenges command triggered by {event.get_user_id()}")
    
    # 限制：如果设置了 ALLOWED_GROUP_IDS，则仅允许来自这些群的 GroupMessageEvent
    if ALLOWED_GROUP_IDS:
        if not isinstance(event, GroupMessageEvent) or getattr(event, "group_id", None) not in ALLOWED_GROUP_IDS:
            print(f"DEBUG: Command blocked - group_id: {getattr(event, 'group_id', None)}, allowed: {ALLOWED_GROUP_IDS}")
            await gamechallenges.finish("此命令仅在指定群聊内可用。")

    if not POSTGRES_DSN:
        print("DEBUG: POSTGRES_DSN not configured")
        await gamechallenges.finish("未配置 POSTGRES_DSN。")
    
    print(f"DEBUG: Connecting to database: {POSTGRES_DSN}")
    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        print("DEBUG: Database connected successfully")
        rows = await conn.fetch('SELECT id, "Title", "IsEnabled" FROM "GameChallenges" ORDER BY id DESC LIMIT 10')
        await conn.close()
        print(f"DEBUG: Query returned {len(rows)} rows")
    except Exception as e:
        print(f"DEBUG: Database error: {e}")
        await gamechallenges.finish(f"查询失败: {e}")

    if not rows:
        print("DEBUG: No rows found")
        await gamechallenges.finish("表中无记录。")
    
    # 简要格式化并发送
    text = "\n".join(f"{r['id']}: {r['Title']} (enabled={r['IsEnabled']})" for r in rows)
    print(f"DEBUG: Sending response: {text[:100]}...")
    try:
        await bot.send(event, text)
        print("DEBUG: Message sent successfully")
    except Exception as e:
        print(f"DEBUG: Failed to send message: {e}")
