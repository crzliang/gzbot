"""
通知系统模块
提供自动通知检查、格式化和播报功能
"""
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum

from nonebot import require, get_driver
from .config import POSTGRES_DSN, TARGET_GAME_ID, ALLOWED_GROUP_IDS
from .database import get_recent_notices, get_challenge_info_by_name, get_game_title
from .utils import format_blood_notification, decode_unicode_values, extract_challenge_name_from_values

# 导入定时任务依赖
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 配置日志
logger = logging.getLogger(__name__)

# 常量定义
class NotificationTypes(Enum):
    """通知类型枚举"""
    NEW_CHALLENGE = "新题目开放"
    HINT_UPDATE = "提示更新"
    ANNOUNCEMENT = "公告通知"
    FIRST_BLOOD = "一血"
    SECOND_BLOOD = "二血"
    THIRD_BLOOD = "三血"

class NotificationConfig:
    """通知配置常量"""
    CHECK_INTERVAL_SECONDS = 10
    MAX_BROADCASTED_NOTICES = 1000
    CLEANUP_THRESHOLD = 500
    TIME_FORMAT = "%Y/%m/%d %H:%M:%S"
    BEIJING_TIMEZONE_OFFSET = 8

# 存储已播报的通知ID，避免重复播报
broadcasted_notices: Set[int] = set()


def format_beijing_time(utc_time: datetime) -> str:
    """将UTC时间转换为北京时间格式
    
    Args:
        utc_time: UTC时间对象
        
    Returns:
        格式化的北京时间字符串
    """
    beijing_time = utc_time + timedelta(hours=NotificationConfig.BEIJING_TIMEZONE_OFFSET)
    return beijing_time.strftime(NotificationConfig.TIME_FORMAT)


def _create_notification_border(title: str) -> str:
    """创建通知边框格式
    
    Args:
        title: 通知标题
        
    Returns:
        带边框的标题字符串
    """
    return f"======【{title}】======"


def _create_fallback_message(title: str, content: str, time_str: str) -> str:
    """创建降级通知消息
    
    Args:
        title: 通知标题
        content: 通知内容
        time_str: 时间字符串
        
    Returns:
        格式化的降级消息
    """
    border_title = _create_notification_border(title)
    return f"{border_title}\n{content}\n时间: {time_str}\n======================="


async def _get_base_notification_data(values: str, publish_time: datetime) -> Dict[str, str]:
    """获取通知的基础数据
    
    Args:
        values: 通知值
        publish_time: 发布时间
        
    Returns:
        包含基础数据的字典
    """
    try:
        game_title = await get_game_title(int(TARGET_GAME_ID))
        time_str = format_beijing_time(publish_time)
        decoded_values = decode_unicode_values(values) or "未知内容"
        
        return {
            "game_title": game_title,
            "time_str": time_str,
            "decoded_values": decoded_values
        }
    except Exception as e:
        logger.error(f"Failed to get base notification data: {e}")
        raise


async def format_new_challenge_notification(values: str, publish_time: datetime) -> Optional[str]:
    """格式化新题目开放通知
    
    Args:
        values: 通知值（题目名称）
        publish_time: 发布时间
        
    Returns:
        格式化的通知消息，如果失败则返回None
    """
    try:
        base_data = await _get_base_notification_data(values, publish_time)
        challenge_info = await get_challenge_info_by_name(int(TARGET_GAME_ID), values)
        
        # 使用专门的函数提取题目名称
        challenge_name = extract_challenge_name_from_values(values)
        
        if challenge_info:
            category_name = challenge_info['categoryname']
            message = (
                f"{_create_notification_border('上题目啦')}\n"
                f"比赛: {base_data['game_title']}\n"
                f"时间: {base_data['time_str']}\n"
                f"类型: {category_name}\n"
                f"赛题: {challenge_name}\n"
                f"======================="
            )
            return message
        else:
            logger.warning(f"Challenge info not found for: {values}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to format new challenge notification: {e}")
        # 降级处理
        time_str = format_beijing_time(publish_time)
        challenge_name = extract_challenge_name_from_values(values)
        return _create_fallback_message("上题目啦", f"新题目开放: {challenge_name}", time_str)


async def format_hint_update_notification(values: str, publish_time: datetime) -> Optional[str]:
    """格式化题目提示更新通知
    
    Args:
        values: 通知值（题目名称）
        publish_time: 发布时间
        
    Returns:
        格式化的通知消息
    """
    try:
        base_data = await _get_base_notification_data(values, publish_time)
        challenge_info = await get_challenge_info_by_name(int(TARGET_GAME_ID), values)
        
        # 使用专门的函数提取题目名称
        challenge_name = extract_challenge_name_from_values(values)
        category_name = challenge_info['categoryname'] if challenge_info else "未知"
        
        message = (
            f"{_create_notification_border('题目提示更新')}\n"
            f"比赛: {base_data['game_title']}\n"
            f"时间: {base_data['time_str']}\n"
            f"类型: {category_name}\n"
            f"赛题: {challenge_name}\n"
            f"======================="
        )
        return message
        
    except Exception as e:
        logger.error(f"Failed to format hint update notification: {e}")
        # 降级处理
        time_str = format_beijing_time(publish_time)
        challenge_name = extract_challenge_name_from_values(values)
        return _create_fallback_message("题目提示更新", f"题目提示更新: {challenge_name}", time_str)


async def format_announcement_notification(values: str, publish_time: datetime) -> str:
    """格式化赛事公告通知
    
    Args:
        values: 通知值（公告内容）
        publish_time: 发布时间
        
    Returns:
        格式化的通知消息
    """
    try:
        base_data = await _get_base_notification_data(values, publish_time)
        
        message = (
            f"{_create_notification_border('赛事公告')}\n"
            f"比赛: {base_data['game_title']}\n"
            f"时间: {base_data['time_str']}\n"
            f"内容: {base_data['decoded_values']}\n"
            f"======================="
        )
        return message
        
    except Exception as e:
        logger.error(f"Failed to format announcement notification: {e}")
        # 降级处理
        time_str = format_beijing_time(publish_time)
        announcement_content = decode_unicode_values(values) or "无内容"
        return _create_fallback_message("赛事公告", f"赛事公告: {announcement_content}", time_str)


async def format_blood_notification_template(notice_type: str, values: str, publish_time: datetime) -> str:
    """格式化一血、二血、三血通知模板
    
    Args:
        notice_type: 通知类型
        values: 通知值
        publish_time: 发布时间
        
    Returns:
        格式化的通知消息
    """
    try:
        formatted_content = format_blood_notification(notice_type, values)
        time_str = format_beijing_time(publish_time)
        
        # 血腥通知类型映射
        blood_type_mapping = {
            NotificationTypes.FIRST_BLOOD.value: ("🥇 一血通知", "🥇"),
            NotificationTypes.SECOND_BLOOD.value: ("🥈 二血通知", "🥈"),
            NotificationTypes.THIRD_BLOOD.value: ("🥉 三血通知", "🥉")
        }
        
        # 确定标题
        title = "🏆 血腥通知"  # 默认标题
        for blood_key, (blood_title, _) in blood_type_mapping.items():
            if blood_key in notice_type:
                title = blood_title
                break
        
        border_title = _create_notification_border(title)
        
        if formatted_content:
            message = f"{border_title}\n{formatted_content}\n时间: {time_str}\n======================="
        else:
            message = f"{border_title}\n{notice_type}\n时间: {time_str}\n======================="
        
        return message
        
    except Exception as e:
        logger.error(f"Failed to format blood notification: {e}")
        # 降级处理
        time_str = format_beijing_time(publish_time)
        return _create_fallback_message("🏆 血腥通知", notice_type, time_str)


def _cleanup_broadcasted_notices() -> None:
    """清理已播报通知记录，防止内存溢出"""
    if len(broadcasted_notices) > NotificationConfig.MAX_BROADCASTED_NOTICES:
        sorted_notices = sorted(broadcasted_notices)
        broadcasted_notices.clear()
        broadcasted_notices.update(sorted_notices[-NotificationConfig.CLEANUP_THRESHOLD:])
        logger.info(f"Cleaned up broadcasted notices, kept {NotificationConfig.CLEANUP_THRESHOLD} recent ones")


async def _get_notification_formatter(notice_type: str):
    """根据通知类型获取对应的格式化函数
    
    Args:
        notice_type: 通知类型
        
    Returns:
        对应的格式化函数，如果不支持则返回None
    """
    formatters = {
        NotificationTypes.NEW_CHALLENGE.value: format_new_challenge_notification,
        NotificationTypes.HINT_UPDATE.value: format_hint_update_notification,
        NotificationTypes.ANNOUNCEMENT.value: format_announcement_notification,
    }
    
    # 检查是否为血腥通知
    blood_types = [NotificationTypes.FIRST_BLOOD.value, NotificationTypes.SECOND_BLOOD.value, NotificationTypes.THIRD_BLOOD.value]
    if any(blood in notice_type for blood in blood_types):
        # 返回一个lambda函数，将notice_type固定传入
        return lambda values, publish_time: format_blood_notification_template(notice_type, values, publish_time)
    
    # 检查其他通知类型
    for key_type, formatter in formatters.items():
        if key_type in notice_type:
            return formatter
    
    return None


async def _broadcast_to_groups(message: str, notice_id: int) -> None:
    """向所有允许的群组播报消息
    
    Args:
        message: 要播报的消息
        notice_id: 通知ID
    """
    driver = get_driver()
    bots = driver.bots
    
    success_count = 0
    total_groups = len(ALLOWED_GROUP_IDS) * len(bots)
    
    for bot in bots.values():
        for group_id in ALLOWED_GROUP_IDS:
            try:
                await bot.send_group_msg(group_id=group_id, message=message)
                success_count += 1
                logger.debug(f"Successfully broadcast notice {notice_id} to group {group_id}")
            except Exception as e:
                logger.error(f"Failed to broadcast to group {group_id}: {e}")
    
    logger.info(f"Broadcast notice {notice_id} to {success_count}/{total_groups} targets")


async def check_and_broadcast_notices() -> None:
    """定时检查并播报新通知"""
    if not all([POSTGRES_DSN, TARGET_GAME_ID, ALLOWED_GROUP_IDS]):
        logger.warning("Auto broadcast not configured properly")
        return
    
    logger.debug("Checking for new notices...")
    
    try:
        # 获取最近的新通知
        rows = await get_recent_notices(int(TARGET_GAME_ID), seconds=NotificationConfig.CHECK_INTERVAL_SECONDS)
        logger.debug(f"Found {len(rows)} new notices in last {NotificationConfig.CHECK_INTERVAL_SECONDS} seconds")
        
        for row in rows:
            notice_id = row['Id']
            
            # 避免重复播报
            if notice_id in broadcasted_notices:
                continue
                
            notice_type = row['notice_type']
            values = row['Values'] or ""
            publish_time = row['PublishTimeUtc']
            
            # 获取格式化函数
            formatter = await _get_notification_formatter(notice_type)
            if not formatter:
                logger.warning(f"No formatter found for notice type: {notice_type}")
                continue
            
            # 格式化消息
            message = await formatter(values, publish_time)
            if not message:
                logger.warning(f"Failed to format message for notice {notice_id}")
                continue
            
            # 播报消息
            await _broadcast_to_groups(message, notice_id)
            
            # 标记为已播报
            broadcasted_notices.add(notice_id)
        
        # 清理过期记录
        _cleanup_broadcasted_notices()
            
    except Exception as e:
        logger.error(f"Auto broadcast error: {e}")


# 设置定时任务，每10秒检查一次新通知，实现近实时播报
@scheduler.scheduled_job(
    "interval", 
    seconds=NotificationConfig.CHECK_INTERVAL_SECONDS, 
    id="auto_broadcast_notices"
)
async def auto_broadcast_job() -> None:
    """定时播报任务 - 实现近实时通知播报"""
    await check_and_broadcast_notices()
