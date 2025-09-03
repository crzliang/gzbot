from nonebot import get_driver

# 这里无需 require 其它模块，app.py 会通过 nonebot.load_plugins("bot") 加载本目录下的所有插件文件

driver = get_driver()

# ...existing code...
