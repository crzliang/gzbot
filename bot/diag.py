from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent
import os

diag = on_command("botstatus", priority=5)

@diag.handle()
async def handle_diag(bot: Bot, event: Event):
    driver = get_driver()
    bots = getattr(driver, 'bots', {})
    res = []
    res.append(f"Connected bots: {list(bots.keys())}")
    # 展示关键配置（环境变量与适配器配置），用于确认发送 API 可用
    api_root_env = os.getenv("ONEBOT_V11_API_ROOT")
    access_token_env = os.getenv("ONEBOT_V11_ACCESS_TOKEN")
    res.append(f"ONEBOT_V11_API_ROOT(env): {api_root_env}")
    res.append(f"ONEBOT_V11_ACCESS_TOKEN(env): {'<set>' if access_token_env else '<empty>'}")
    # NoneBot 配置对象中（若适配器读取到会存在以下字段）
    api_root_cfg = getattr(driver.config, 'onebot_v11_api_root', None)
    access_token_cfg = getattr(driver.config, 'onebot_v11_access_token', None)
    res.append(f"onebot_v11_api_root(cfg): {api_root_cfg}")
    res.append(f"onebot_v11_access_token(cfg): {'<set>' if access_token_cfg else '<empty>'}")

    # 尝试基础 API 调用，验证 HTTP API 是否可用
    try:
        status = await bot.call_api("get_status")
        res.append(f"get_status ok: {status}")
    except Exception as e:
        res.append(f"get_status failed: {e}")
    try:
        login = await bot.call_api("get_login_info")
        res.append(f"get_login_info ok: {login}")
    except Exception as e:
        res.append(f"get_login_info failed: {e}")

    # 如果是在群里，尝试发送一条测试消息给该群
    if isinstance(event, GroupMessageEvent):
        gid = event.group_id
        res.append(f"Triggered in group: {gid}")
        try:
            # 使用 OneBot v11 API 调用发送群消息
            await bot.call_api("send_group_msg", {"group_id": gid, "message": "测试：机器人可以发送消息"})
            res.append("试发消息已发送（send_group_msg 调用成功）")
        except Exception as e:
            res.append(f"试发消息失败: {e}")
    else:
        res.append("非群消息触发：未尝试发送测试群消息。")

    await diag.finish("\n".join(res))
