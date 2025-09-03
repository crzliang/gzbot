"""
命令处理模块
"""
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent
import re
from .config import ALLOWED_GROUP_IDS, POSTGRES_DSN, TARGET_GAME_ID
from .database import get_game_title, get_game_challenges, get_game_rankings, get_game_rankings_by_stdnum_prefix
from .utils import format_challenges_message, format_ranking_message


# 定义命令触发
gamechallenges = on_command("gamechallenges", aliases={"gc"}, priority=5)
rank = on_command("rank", priority=5)
help_command = on_command("help", priority=5)
# 使用正则表达式匹配 rank-xx 格式的命令
rank_prefix = on_regex(r'^/rank-(\d+)$', priority=4)


def check_group_permission(event: Event) -> bool:
    """检查群组权限"""
    if ALLOWED_GROUP_IDS:
        if not isinstance(event, GroupMessageEvent) or getattr(event, "group_id", None) not in ALLOWED_GROUP_IDS:
            return False
    return True


@gamechallenges.handle()
async def handle_gc(bot: Bot, event: Event):
    print(f"DEBUG: gamechallenges command triggered by {event.get_user_id()}")
    
    # 限制：如果设置了 ALLOWED_GROUP_IDS，则仅允许来自这些群的 GroupMessageEvent
    if not check_group_permission(event):
        print(f"DEBUG: Command blocked - group_id: {getattr(event, 'group_id', None)}, allowed: {ALLOWED_GROUP_IDS}")
        return  # 静默处理，不发送任何消息

    if not POSTGRES_DSN:
        print("DEBUG: POSTGRES_DSN not configured")
        await gamechallenges.finish("未配置 POSTGRES_DSN。")
    
    if not TARGET_GAME_ID:
        await gamechallenges.finish("未在 .env 文件中设置 TARGET_GAME_ID。")

    print(f"DEBUG: Connecting to database: {POSTGRES_DSN}")
    
    try:
        # 获取游戏标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        print(f"DEBUG: Found game title: '{game_title}' for GameId={TARGET_GAME_ID}")

        # 获取题目列表
        challenges_data = await get_game_challenges(int(TARGET_GAME_ID))
        print(f"DEBUG: Query for GameId={TARGET_GAME_ID} returned {len(challenges_data)} rows")
        
        if not challenges_data:
            print("DEBUG: No rows found")
            await gamechallenges.finish(f"在比赛 '{game_title}' 中未找到任何赛题。")
        
        # 格式化并发送消息
        text = format_challenges_message(game_title, challenges_data)
        print(f"DEBUG: Sending response: {text[:200]}...")
        
        await bot.send(event, text)
        print("DEBUG: Message sent successfully")
        
    except Exception as e:
        print(f"DEBUG: Database error: {e}")
        await gamechallenges.finish(f"查询失败！")


@rank.handle()
async def handle_rank(bot: Bot, event: Event):
    print(f"DEBUG: rank command triggered by {event.get_user_id()}")
    
    # 限制：如果设置了 ALLOWED_GROUP_IDS，则仅允许来自这些群的 GroupMessageEvent
    if not check_group_permission(event):
        print(f"DEBUG: Command blocked - group_id: {getattr(event, 'group_id', None)}, allowed: {ALLOWED_GROUP_IDS}")
        return  # 静默处理，不发送任何消息

    if not POSTGRES_DSN:
        print("DEBUG: POSTGRES_DSN not configured")
        await rank.finish("未配置 POSTGRES_DSN。")
    
    if not TARGET_GAME_ID:
        await rank.finish("未在 .env 文件中设置 TARGET_GAME_ID。")

    print(f"DEBUG: Connecting to database for rank query: {POSTGRES_DSN}")
    
    try:
        # 获取游戏标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        print(f"DEBUG: Found game title: '{game_title}' for rank query GameId={TARGET_GAME_ID}")

        # 获取排行榜数据
        ranking_data = await get_game_rankings(int(TARGET_GAME_ID))
        print(f"DEBUG: Rank query for GameId={TARGET_GAME_ID} returned {len(ranking_data)} teams")
        
        if not ranking_data:
            print("DEBUG: No ranking data found")
            await rank.finish(f"比赛 '{game_title}' 暂无排行榜数据。")
        
        # 格式化并发送消息
        text = format_ranking_message(game_title, ranking_data)
        print(f"DEBUG: Sending rank response: {text[:200]}...")
        
        await bot.send(event, text)
        print("DEBUG: Rank message sent successfully")
        
    except Exception as e:
        print(f"DEBUG: Rank database error: {e}")
        await rank.finish(f"查询排行榜失败！")


@help_command.handle()
async def handle_help(bot: Bot, event: Event):
    """处理帮助命令"""
    print(f"DEBUG: help command triggered by {event.get_user_id()}")
    
    # 权限检查
    if not check_group_permission(event):
        print(f"DEBUG: Help command blocked - group_id: {getattr(event, 'group_id', None)}, allowed: {ALLOWED_GROUP_IDS}")
        return  # 静默处理，不发送任何消息

    help_text = """
可用命令：
• /help - 显示此帮助信息
• /gc 或 /gamechallenges - 查看比赛题目列表
• /rank - 查看排行榜
• /rank-XX - 查看指定级别排行榜（如：/rank-25）

如有问题，请联系管理员。
    """.strip()
    
    try:
        await bot.send(event, help_text)
        print("DEBUG: Help message sent successfully")
    except Exception as e:
        print(f"DEBUG: Failed to send help message: {e}")


@rank_prefix.handle()
async def handle_rank_prefix(bot: Bot, event: Event):
    """处理带学号前缀的排行榜查询，如 /rank-25"""
    print(f"DEBUG: rank-prefix command triggered by {event.get_user_id()}")
    
    # 权限检查
    if not check_group_permission(event):
        print(f"DEBUG: Command blocked - group_id: {getattr(event, 'group_id', None)}, allowed: {ALLOWED_GROUP_IDS}")
        return  # 静默处理，不发送任何消息

    if not POSTGRES_DSN:
        print("DEBUG: POSTGRES_DSN not configured")
        await rank_prefix.finish("未配置 POSTGRES_DSN。")
    
    if not TARGET_GAME_ID:
        await rank_prefix.finish("未在 .env 文件中设置 TARGET_GAME_ID。")

    # 从消息中提取学号前缀
    message_text = str(event.get_message()).strip()
    match = re.search(r'/rank-(\d+)', message_text)
    if not match:
        await rank_prefix.finish("请使用正确格式，例如：/rank-25")
        return
    
    prefix_str = match.group(1)
    
    try:
        print(f"DEBUG: Connecting to database for rank-prefix query: {POSTGRES_DSN}")
        
        # 获取游戏标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        print(f"DEBUG: Found game title: '{game_title}' for rank-prefix query GameId={TARGET_GAME_ID}")

        # 获取按学号前缀过滤的排行榜数据
        ranking_data = await get_game_rankings_by_stdnum_prefix(int(TARGET_GAME_ID), prefix_str)
        print(f"DEBUG: Rank-prefix query for GameId={TARGET_GAME_ID}, prefix={prefix_str} returned {len(ranking_data)} teams")
        
        if not ranking_data:
            print("DEBUG: No ranking data found for prefix")
            await rank_prefix.finish(f"'{game_title}' 赛事中未找到{prefix_str}级的队伍。")
        
        # 格式化并发送消息，标题包含前缀信息
        text = format_ranking_message(f"{game_title} - {prefix_str} 级", ranking_data)
        print(f"DEBUG: Sending rank-prefix response: {text[:200]}...")
        
        await bot.send(event, text)
        print("DEBUG: Rank-prefix message sent successfully")
        
    except Exception as e:
        print(f"DEBUG: Rank-prefix database error: {e}")
        await rank_prefix.finish(f"查询排行榜失败！")
