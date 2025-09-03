"""
通知系统模块
"""
from nonebot import require, get_driver
from .config import POSTGRES_DSN, TARGET_GAME_ID, ALLOWED_GROUP_IDS
from .database import get_recent_notices
from .utils import format_blood_notification

# 导入定时任务依赖
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 存储已播报的通知ID，避免重复播报
broadcasted_notices = set()


async def check_and_broadcast_notices():
    """定时检查并播报新通知"""
    if not POSTGRES_DSN or not TARGET_GAME_ID or not ALLOWED_GROUP_IDS:
        print("DEBUG: Auto broadcast not configured properly")
        return
    
    print("DEBUG: Checking for new notices...")
    
    try:
        # 获取最近10秒内的新通知
        rows = await get_recent_notices(int(TARGET_GAME_ID), seconds=10)
        print(f"DEBUG: Found {len(rows)} new notices in last 10 seconds")
        
        driver = get_driver()
        bots = driver.bots
        
        for row in rows:
            notice_id = row['Id']  # 注意大写I
            
            # 避免重复播报
            if notice_id in broadcasted_notices:
                continue
                
            notice_type = row['notice_type']
            values = row['Values'] or ""  # 注意大写V
            publish_time = row['PublishTimeUtc']  # 注意大写
            
            # 使用新的格式化函数处理前三血通知
            formatted_content = format_blood_notification(notice_type, values)
            
            # 格式化播报消息
            time_str = publish_time.strftime("时间：%y/%m/%d %H:%M:%S")
            message = f"赛事通知自动播报\n\n{notice_type}"
            if formatted_content:
                # 所有通知都直接显示内容，不加前缀
                message += f"\n{formatted_content}"
            # 添加时间显示
            message += f"\n{time_str}"
            
            # 向所有允许的群组播报
            for bot in bots.values():
                for group_id in ALLOWED_GROUP_IDS:
                    try:
                        await bot.send_group_msg(group_id=group_id, message=message)
                        print(f"DEBUG: Auto broadcast notice {notice_id} to group {group_id}")
                    except Exception as e:
                        print(f"DEBUG: Failed to broadcast to group {group_id}: {e}")
            
            # 标记为已播报
            broadcasted_notices.add(notice_id)
        
        # 清理过期的播报记录（保留最近1000条）
        if len(broadcasted_notices) > 1000:
            sorted_notices = sorted(broadcasted_notices)
            broadcasted_notices.clear()
            broadcasted_notices.update(sorted_notices[-500:])
            
    except Exception as e:
        print(f"DEBUG: Auto broadcast error: {e}")


# 设置定时任务，每10秒检查一次新通知，实现近实时播报
@scheduler.scheduled_job("interval", seconds=10, id="auto_broadcast_notices")
async def auto_broadcast_job():
    """定时播报任务 - 10秒检查一次实现近实时"""
    await check_and_broadcast_notices()
