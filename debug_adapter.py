import nonebot
from nonebot.adapters.onebot.v11 import Adapter

# 初始化并检查适配器信息
nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter(Adapter)

# 获取适配器实例
adapters = driver._adapters
print("Registered adapters:", list(adapters.keys()))
print("Driver type:", type(driver))

# 检查 ASGI 应用的路由
app = nonebot.get_asgi()
print("App type:", type(app))

# 尝试检查路由
if hasattr(app, 'routes'):
    print("Routes:", app.routes)
elif hasattr(app, 'router'):
    print("Router:", app.router)
    if hasattr(app.router, 'routes'):
        print("Router routes:", app.router.routes)

# 检查 OneBot 适配器配置
print("OneBot config keys:", list(driver.config.__dict__.keys()))
