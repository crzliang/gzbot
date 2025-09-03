"""
通知系统模块：自动播报
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

from nonebot import get_driver, require

from .config import ALLOWED_GROUP_IDS, TARGET_GAME_ID
from .database import get_recent_notices, get_challenge_info_by_name, get_game_title
from .utils import (
    decode_unicode_values,
    extract_challenge_name_from_values,
    format_blood_notification,
)

# 依赖定时任务插件
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

logger = logging.getLogger(__name__)


class NotificationTypes(str, Enum):
    NEW_CHALLENGE = "新题目开放"
    HINT_UPDATE = "提示更新"
    ANNOUNCEMENT = "公告通知"
    FIRST_BLOOD = "一血"
    SECOND_BLOOD = "二血"
    THIRD_BLOOD = "三血"


@dataclass
class NotificationConfig:
    CHECK_INTERVAL_SECONDS: int = 10
    MAX_BROADCASTED_NOTICES: int = 1000
    CLEANUP_THRESHOLD: int = 500
    TIME_FORMAT: str = "%Y/%m/%d %H:%M:%S"
    BEIJING_TZ: timezone = timezone(timedelta(hours=8))


# 状态
broadcasted_notices: Set[int] = set()
last_checked_time: Optional[datetime] = None  # UTC
AUTO_BROADCAST_ENABLED: bool = False


def is_auto_broadcast_enabled() -> bool:
    return AUTO_BROADCAST_ENABLED


def set_auto_broadcast_enabled(enabled: bool) -> None:
    global AUTO_BROADCAST_ENABLED, last_checked_time
    AUTO_BROADCAST_ENABLED = enabled
    if enabled:
        # 以系统当前时间作为水位线（UTC）
        last_checked_time = datetime.now(timezone.utc)


# 时间/格式化

def _fmt_bj(utc_dt: datetime) -> str:
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    bj = utc_dt.astimezone(NotificationConfig.BEIJING_TZ)
    return bj.strftime(NotificationConfig.TIME_FORMAT)


def _border(title: str) -> str:
    return f"======【{title}】======"


def _fallback(title: str, content: str, publish_time: datetime) -> str:
    return f"{_border(title)}\n{content}\n时间: {_fmt_bj(publish_time)}\n======================="


async def _base(values: str, publish_time: datetime) -> Dict[str, str]:
    game_title = await get_game_title(int(TARGET_GAME_ID))
    return {
        "game_title": game_title,
        "time_str": _fmt_bj(publish_time),
        "decoded_values": decode_unicode_values(values) or "未知内容",
    }


async def _fmt_new(values: str, publish_time: datetime) -> Optional[str]:
    try:
        base = await _base(values, publish_time)
        info = await get_challenge_info_by_name(int(TARGET_GAME_ID), values)
        name = extract_challenge_name_from_values(values)
        if info:
            category = info.get("categoryname", "未知")
            return (
                f"{_border('上题目啦')}\n"
                f"比赛: {base['game_title']}\n"
                f"时间: {base['time_str']}\n"
                f"类型: {category}\n"
                f"赛题: {name}\n"
                f"======================="
            )
        return None
    except Exception as e:
        logger.exception("format new challenge failed: %s", e)
        return _fallback("上题目啦", f"新题目开放: {extract_challenge_name_from_values(values)}", publish_time)


async def _fmt_hint(values: str, publish_time: datetime) -> Optional[str]:
    try:
        base = await _base(values, publish_time)
        info = await get_challenge_info_by_name(int(TARGET_GAME_ID), values)
        name = extract_challenge_name_from_values(values)
        category = info.get("categoryname", "未知") if info else "未知"
        return (
            f"{_border('题目提示更新')}\n"
            f"比赛: {base['game_title']}\n"
            f"时间: {base['time_str']}\n"
            f"类型: {category}\n"
            f"赛题: {name}\n"
            f"======================="
        )
    except Exception as e:
        logger.exception("format hint failed: %s", e)
        return _fallback("题目提示更新", f"题目提示更新: {extract_challenge_name_from_values(values)}", publish_time)


async def _fmt_announce(values: str, publish_time: datetime) -> str:
    try:
        base = await _base(values, publish_time)
        return (
            f"{_border('赛事公告')}\n"
            f"比赛: {base['game_title']}\n"
            f"时间: {base['time_str']}\n"
            f"内容: {base['decoded_values']}\n"
            f"======================="
        )
    except Exception as e:
        logger.exception("format announcement failed: %s", e)
        return _fallback("赛事公告", f"赛事公告: {decode_unicode_values(values) or '无内容'}", publish_time)


async def _fmt_blood_wrapper(notice_type: str, values: str, publish_time: datetime) -> str:
    try:
        content = format_blood_notification(notice_type, values)
        title = "🏆 血腥通知"
        if NotificationTypes.FIRST_BLOOD.value in notice_type:
            title = "🥇 一血通知"
        elif NotificationTypes.SECOND_BLOOD.value in notice_type:
            title = "🥈 二血通知"
        elif NotificationTypes.THIRD_BLOOD.value in notice_type:
            title = "🥉 三血通知"
        body = content or notice_type
        return f"{_border(title)}\n{body}\n时间: {_fmt_bj(publish_time)}\n======================="
    except Exception as e:
        logger.exception("format blood failed: %s", e)
        return _fallback("🏆 血腥通知", notice_type, publish_time)


async def _formatter_for(notice_type: str) -> Optional[Callable[[str, datetime], Optional[str]]]:
    # 映射普通类型
    mapping: Dict[str, Callable[[str, datetime], Optional[str]]] = {
        NotificationTypes.NEW_CHALLENGE.value: _fmt_new,
        NotificationTypes.HINT_UPDATE.value: _fmt_hint,
        NotificationTypes.ANNOUNCEMENT.value: _fmt_announce,
    }
    for key, func in mapping.items():
        if key in notice_type:
            return func
    # 血类
    blood_keys = [
        NotificationTypes.FIRST_BLOOD.value,
        NotificationTypes.SECOND_BLOOD.value,
        NotificationTypes.THIRD_BLOOD.value,
    ]
    if any(k in notice_type for k in blood_keys):
        return lambda v, t: _fmt_blood_wrapper(notice_type, v, t)
    return None


async def _broadcast_to_groups(message: str, notice_id: int) -> None:
    driver = get_driver()
    bots = driver.bots
    success = 0
    targets = len(ALLOWED_GROUP_IDS) * max(1, len(bots))
    for bot in bots.values():
        for gid in ALLOWED_GROUP_IDS:
            try:
                await bot.send_group_msg(group_id=gid, message=message)
                success += 1
            except Exception as e:
                logger.error("broadcast group %s failed: %s", gid, e)
    logger.info("Broadcast notice %s to %s/%s targets", notice_id, success, targets)


def _cleanup() -> None:
    if len(broadcasted_notices) > NotificationConfig.MAX_BROADCASTED_NOTICES:
        kept = sorted(broadcasted_notices)[-NotificationConfig.CLEANUP_THRESHOLD :]
        broadcasted_notices.clear()
        broadcasted_notices.update(kept)
        logger.info("cleanup broadcasted set, kept %d", len(kept))


async def check_and_broadcast_notices() -> None:
    if not ALLOWED_GROUP_IDS or not TARGET_GAME_ID:
        logger.warning("auto broadcast not configured")
        return
    if not is_auto_broadcast_enabled():
        return

    global last_checked_time
    now = datetime.now(timezone.utc)
    if last_checked_time is None:
        last_checked_time = now
        return

    window_seconds = int((now - last_checked_time).total_seconds())
    if window_seconds <= 0:
        window_seconds = NotificationConfig.CHECK_INTERVAL_SECONDS

    # 暂时禁用实际查询，避免回放
    rows: List[Dict] = []
    # rows = await get_recent_notices(int(TARGET_GAME_ID), seconds=window_seconds)

    for row in rows:
        notice_id = row["Id"]
        if notice_id in broadcasted_notices:
            continue
        notice_type = row["notice_type"]
        values = row.get("Values") or ""
        publish_time = row["PublishTimeUtc"]

        formatter = await _formatter_for(notice_type)
        if not formatter:
            logger.warning("no formatter for type: %s", notice_type)
            continue
        msg = await formatter(values, publish_time)
        if not msg:
            logger.warning("format message failed for %s", notice_id)
            continue

        await _broadcast_to_groups(msg, notice_id)
        broadcasted_notices.add(notice_id)
        _cleanup()

    last_checked_time = now


@scheduler.scheduled_job(
    "interval", seconds=NotificationConfig.CHECK_INTERVAL_SECONDS, id="auto_broadcast_notices"
)
async def auto_broadcast_job() -> None:
    await check_and_broadcast_notices()
