"""
命令处理模块
"""
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event
import re
from .config import TARGET_GAME_ID
from .database import get_game_title, get_game_challenges, get_game_rankings, get_game_rankings_by_stdnum_prefix
from .utils import (
    format_challenges_message, 
    format_ranking_message,
    validate_command_prerequisites, 
    send_response, 
    log_command_result, 
    log_database_error,
    check_admin_permission
)
from .notifications import set_auto_broadcast_enabled, is_auto_broadcast_enabled


# 定义命令触发
gamechallenges = on_command("gamechallenges", aliases={"gc"}, priority=5)
rank = on_command("rank", priority=5)
help_command = on_command("help", priority=5)
# 自动播报控制命令
open_broadcast = on_command("open", priority=5)
close_broadcast = on_command("close", priority=5)
# 使用正则表达式匹配 rank-xx 格式的命令（仅两位数字）
rank_prefix = on_regex(r'^/rank-(\d{2})$', priority=4)


@gamechallenges.handle()
async def handle_gc(bot: Bot, event: Event):
    """处理题目列表查询命令"""
    # 验证先决条件
    error_msg = await validate_command_prerequisites("gamechallenges", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await gamechallenges.finish(error_msg)

    try:
        # 获取赛事标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        
        # 获取题目列表
        challenges_data = await get_game_challenges(int(TARGET_GAME_ID))
        log_command_result("gamechallenges", int(TARGET_GAME_ID), len(challenges_data), "challenges")
        
        if not challenges_data:
            await gamechallenges.finish(f"在比赛 '{game_title}' 中未找到任何赛题。")
        
        # 格式化并发送消息
        text = format_challenges_message(game_title, challenges_data)
        await send_response(bot, event, text, "gamechallenges")
        
    except Exception as e:
        log_database_error("gamechallenges", e)
        await gamechallenges.finish("查询失败！")


@rank.handle()
async def handle_rank(bot: Bot, event: Event):
    """处理排行榜查询命令"""
    # 验证先决条件
    error_msg = await validate_command_prerequisites("rank", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await rank.finish(error_msg)

    try:
        # 获取赛事标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        
        # 获取排行榜数据
        ranking_data = await get_game_rankings(int(TARGET_GAME_ID))
        log_command_result("rank", int(TARGET_GAME_ID), len(ranking_data), "teams")
        
        if not ranking_data:
            await rank.finish(f"比赛 '{game_title}' 暂无排行榜数据。")
        
        # 格式化并发送消息
        text = format_ranking_message(game_title, ranking_data)
        await send_response(bot, event, text, "rank")
        
    except Exception as e:
        log_database_error("rank", e)
        await rank.finish("查询排行榜失败！")


@help_command.handle()
async def handle_help(bot: Bot, event: Event):
    """处理帮助命令"""
    # 只需要权限检查，不需要数据库配置
    error_msg = await validate_command_prerequisites("help", event)
    if error_msg == "PERMISSION_DENIED":
        return  # 静默处理权限拒绝

    help_text = """
帮助文档

普通用户可用命令：
• /help - 显示此帮助信息
• /gc 或 /gamechallenges - 查看比赛题目列表
• /rank - 查看排行榜
• /rank-XX - 查看指定级别排行榜（如：/rank-25）

管理员可用命令
• /open - 开启自动播报(一血、二血、三血、上新题、题目加提示、赛事公告)
• /close - 关闭自动播报(一血、二血、三血、上新题、题目加提示、赛事公告)

注意：自动播报默认关闭，请使用 /open 开启，/close 关闭。
    """.strip()
    
    try:
        await send_response(bot, event, help_text, "help")
    except Exception as e:
        log_database_error("help", e)


@open_broadcast.handle()
async def handle_open_broadcast(bot: Bot, event: Event):
    """开启自动播报"""
    # 检查管理员权限
    if not check_admin_permission(event):
        await send_response(bot, event, "权限不足，只有管理员才能执行此命令。", "open")
        return
    
    # 只做权限检查
    error_msg = await validate_command_prerequisites("open", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return
        await open_broadcast.finish(error_msg)
    
    try:
        if is_auto_broadcast_enabled():
            await send_response(bot, event, "自动播报已是开启状态。", "open")
            return
        set_auto_broadcast_enabled(True)
        await send_response(bot, event, "已开启自动播报。", "open")
    except Exception as e:
        log_database_error("open", e)


@close_broadcast.handle()
async def handle_close_broadcast(bot: Bot, event: Event):
    """关闭自动播报"""
    # 检查管理员权限
    if not check_admin_permission(event):
        await send_response(bot, event, "权限不足，只有管理员才能执行此命令。", "close")
        return
    
    # 只做权限检查
    error_msg = await validate_command_prerequisites("close", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return
        await close_broadcast.finish(error_msg)
    
    try:
        if not is_auto_broadcast_enabled():
            await send_response(bot, event, "自动播报已是关闭状态。", "close")
            return
        set_auto_broadcast_enabled(False)
        await send_response(bot, event, "已关闭自动播报。", "close")
    except Exception as e:
        log_database_error("close", e)


@rank_prefix.handle()
async def handle_rank_prefix(bot: Bot, event: Event):
    """处理带学号前缀的排行榜查询，如 /rank-25"""
    # 验证先决条件
    error_msg = await validate_command_prerequisites("rank-prefix", event)
    if error_msg:
        if error_msg == "PERMISSION_DENIED":
            return  # 静默处理权限拒绝
        await rank_prefix.finish(error_msg)

    # 从消息中提取学号前缀
    message_text = str(event.get_message()).strip()
    match = re.search(r'/rank-(\d{2})', message_text)
    if not match:
        await rank_prefix.finish("请使用正确格式，例如：/rank-25")
        return
    
    prefix_str = match.group(1)
    
    try:
        # 获取赛事标题
        game_title = await get_game_title(int(TARGET_GAME_ID))
        
        # 获取按学号前缀过滤的排行榜数据
        ranking_data = await get_game_rankings_by_stdnum_prefix(int(TARGET_GAME_ID), prefix_str)
        log_command_result("rank-prefix", int(TARGET_GAME_ID), len(ranking_data), f"teams (prefix={prefix_str})")
        
        if not ranking_data:
            await rank_prefix.finish(f"'{game_title}' 赛事中未找到{prefix_str}级的队伍。")
        
        # 格式化并发送消息，标题包含前缀信息
        text = format_ranking_message(f"{game_title} - {prefix_str} 级", ranking_data)
        await send_response(bot, event, text, "rank-prefix")
        
    except Exception as e:
        log_database_error("rank-prefix", e)
        await rank_prefix.finish("查询排行榜失败！")
