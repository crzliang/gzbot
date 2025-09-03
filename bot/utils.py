"""
工具函数模块
提供Unicode解码、通知格式化、消息格式化、命令处理等通用功能
"""
import json
import codecs
import logging
from typing import Any, Dict, List, Optional, Union
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent

logger = logging.getLogger(__name__)


def decode_unicode_values(values_str: Optional[str]) -> str:
    """解码 Unicode 编码的 values 字符串
    
    Args:
        values_str: 可能包含Unicode编码的字符串
        
    Returns:
        解码后的字符串，解码失败时返回原字符串
    """
    if not values_str:
        return ""
    
    try:
        # 尝试解析 JSON 格式的 Unicode 编码
        if values_str.startswith('"') and values_str.endswith('"'):
            # 移除首尾引号然后解码
            decoded = json.loads(values_str)
            return decoded
        elif '\\u' in values_str:
            # 直接解码 Unicode 转义序列
            decoded = codecs.decode(values_str, 'unicode_escape')
            return decoded
        else:
            # 如果没有编码，直接返回
            return values_str
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        logger.warning(f"Failed to decode values '{values_str[:50]}...': {e}")
        return values_str  # 解码失败时返回原始字符串


def extract_challenge_name_from_values(values_str: str) -> str:
    """从新题目通知的values中提取题目名称
    
    Args:
        values_str: 题目通知的值，可能是 ["题目名"] 格式
        
    Returns:
        提取的题目名称
    """
    try:
        # 先进行Unicode解码
        decoded = decode_unicode_values(values_str)
        
        # 如果解码后是JSON数组格式，提取第一个元素
        if decoded.startswith('[') and decoded.endswith(']'):
            try:
                parsed_list = json.loads(decoded)
                if isinstance(parsed_list, list) and len(parsed_list) > 0:
                    return str(parsed_list[0])
            except json.JSONDecodeError:
                pass
        
        # 如果不是数组格式，直接返回解码结果
        return decoded
        
    except Exception as e:
        logger.warning(f"Failed to extract challenge name from '{values_str}': {e}")
        return values_str or "未知题目"


def _parse_blood_notification_values(decoded_values: Any) -> Optional[tuple[str, str]]:
    """解析血腥通知的值
    
    Args:
        decoded_values: 解码后的值
        
    Returns:
        元组(队伍名, 题目名)，解析失败返回None
    """
    try:
        # 尝试解析为JSON数组
        if isinstance(decoded_values, str):
            try:
                values_list = json.loads(decoded_values)
            except json.JSONDecodeError:
                values_list = decoded_values
        else:
            values_list = decoded_values
        
        # 如果是列表格式 ["队伍名", "题目名"]
        if isinstance(values_list, list) and len(values_list) >= 2:
            return values_list[0], values_list[1]
        
        return None
    except Exception as e:
        logger.error(f"Failed to parse blood notification values: {e}")
        return None


def _get_blood_type_info(notice_type: str) -> Optional[tuple[str, str]]:
    """获取血腥通知类型信息
    
    Args:
        notice_type: 通知类型字符串
        
    Returns:
        元组(血腥类型, 表情)，未识别返回None
    """
    blood_mapping = {
        "一血": ("一血", "🥇"),
        "二血": ("二血", "🥈"),
        "三血": ("三血", "�")
    }
    
    for blood_key, (blood_type, emoji) in blood_mapping.items():
        if blood_key in notice_type:
            return blood_type, emoji
    
    return None


def format_blood_notification(notice_type: str, values_str: str) -> str:
    """格式化血腥通知的显示内容
    
    Args:
        notice_type: 通知类型
        values_str: 通知值字符串
        
    Returns:
        格式化后的通知内容
    """
    try:
        decoded_values = decode_unicode_values(values_str)
        
        # 检查是否为前三血通知
        if any(blood in notice_type for blood in ['一血', '二血', '三血']):
            blood_info = _parse_blood_notification_values(decoded_values)
            
            if blood_info:
                team_name, challenge_name = blood_info
                blood_type_info = _get_blood_type_info(notice_type)
                
                if blood_type_info:
                    blood_type, _ = blood_type_info
                    return f"恭喜 {team_name} 获得 [{challenge_name}] {blood_type}"
            
            # 如果解析失败，返回原始解码值
            return str(decoded_values) if decoded_values else ""
        
        # 检查其他通知类型
        elif '新题目开放' in notice_type:
            challenge_name = str(decoded_values) if decoded_values else "未知题目"
            return f"题目 [{challenge_name}] 已开放"
        
        elif '提示更新' in notice_type:
            challenge_name = str(decoded_values) if decoded_values else "未知题目"
            return f"题目 [{challenge_name}] 更新了提示"
        
        else:
            # 其他通知，直接返回解码后的内容
            return str(decoded_values) if decoded_values else ""
            
    except Exception as e:
        logger.error(f"Failed to format notification: {e}")
        return str(decoded_values) if 'decoded_values' in locals() and decoded_values else ""


def format_challenges_message(game_title: str, challenges_data: List[Dict[str, Any]]) -> str:
    """格式化题目列表消息
    
    Args:
        game_title: 比赛标题
        challenges_data: 题目数据列表
        
    Returns:
        格式化的题目列表消息
    """
    from .config import CATEGORY_MAPPING
    
    if not challenges_data:
        return f"--- {game_title} -- 题目列表 ---\n暂无题目"
    
    text_lines = [f"--- {game_title} -- 题目列表 ---"]
    
    # 按 Category 分组
    category_groups: Dict[str, List[Dict[str, Any]]] = {}
    for challenge in challenges_data:
        category = challenge.get('Category', 'Unknown')
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(challenge)
    
    # 按 Category 排序并生成消息
    for category in sorted(category_groups.keys()):
        category_name = CATEGORY_MAPPING.get(category, f"未知类型({category})")
        text_lines.append(f"\n【{category_name}】")
        
        # 按分数排序题目
        sorted_challenges = sorted(
            category_groups[category], 
            key=lambda x: x.get('OriginalScore', 0)
        )
        
        for challenge in sorted_challenges:
            title = challenge.get('Title', '未知题目')
            score = challenge.get('OriginalScore', 0)
            text_lines.append(f"  {title} -- {score}分")
    
    return "\n".join(text_lines)


def format_ranking_message(game_title: str, ranking_data: List[Dict[str, Any]]) -> str:
    """格式化排行榜消息
    
    Args:
        game_title: 比赛标题
        ranking_data: 排行榜数据列表
        
    Returns:
        格式化的排行榜消息
    """
    if not ranking_data:
        return f"{game_title} - 排行榜\n" + "=" * 30 + "\n暂无排名数据"
    
    text_lines = [f"{game_title} - 排行榜"]
    text_lines.append("=" * 30)
    
    # 排名表情映射
    rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    for row in ranking_data:
        rank_num = row.get('rank', 0)
        team_name = row.get('teamname', '未知队伍')
        score = row.get('totalscore', 0)
        
        # 添加排名表情
        emoji = rank_emojis.get(rank_num, f" {rank_num} ")
        
        # 只显示队伍名和分数，不显示学号
        text_lines.append(f"{emoji} {team_name} -- {score}分")
    
    return "\n".join(text_lines)


# ==================== 命令处理工具函数 ====================

def check_group_permission(event: Event) -> bool:
    """检查群组权限
    
    Args:
        event: 事件对象
        
    Returns:
        是否有权限
    """
    from .config import ALLOWED_GROUP_IDS
    
    if ALLOWED_GROUP_IDS:
        if not isinstance(event, GroupMessageEvent) or getattr(event, "group_id", None) not in ALLOWED_GROUP_IDS:
            return False
    return True


async def validate_command_prerequisites(command_name: str, event: Event) -> Optional[str]:
    """验证命令执行的先决条件
    
    Args:
        command_name: 命令名称
        event: 事件对象
        
    Returns:
        如果有错误返回错误消息，否则返回None
    """
    from .config import POSTGRES_DSN, TARGET_GAME_ID
    
    logger.debug(f"{command_name} command triggered by {event.get_user_id()}")
    
    # 权限检查
    if not check_group_permission(event):
        logger.debug(f"Command blocked - group_id: {getattr(event, 'group_id', None)}")
        return "PERMISSION_DENIED"  # 特殊标记，表示权限被拒绝
    
    # 配置检查
    if not POSTGRES_DSN:
        logger.debug("POSTGRES_DSN not configured")
        return "未配置 POSTGRES_DSN。"
    
    if not TARGET_GAME_ID:
        return "未在 .env 文件中设置 TARGET_GAME_ID。"
    
    logger.debug(f"Connecting to database: {POSTGRES_DSN}")
    return None


async def send_response(bot: Bot, event: Event, message: str, command_name: str) -> None:
    """发送响应消息
    
    Args:
        bot: 机器人实例
        event: 事件对象
        message: 要发送的消息
        command_name: 命令名称
    """
    try:
        await bot.send(event, message)
        logger.debug(f"{command_name} message sent successfully")
    except Exception as e:
        logger.error(f"Failed to send {command_name} message: {e}")
        raise


def log_command_result(command_name: str, game_id: int, result_count: int, data_type: str = "items") -> None:
    """记录命令执行结果
    
    Args:
        command_name: 命令名称
        game_id: 赛事ID
        result_count: 结果数量
        data_type: 数据类型描述
    """
    logger.debug(f"{command_name} query for GameId={game_id} returned {result_count} {data_type}")


def log_database_error(command_name: str, error: Exception) -> None:
    """记录数据库错误
    
    Args:
        command_name: 命令名称
        error: 异常对象
    """
    logger.error(f"{command_name} database error: {error}")
