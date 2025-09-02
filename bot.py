import os
import nonebot
import uvicorn

if __name__ == "__main__":
    # 加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv()
    
    # 使用 nonebot.run() 而不是手动配置
    nonebot.init()
    # 显式加载 OneBot v11 适配器
    from nonebot.adapters.onebot.v11 import Adapter
    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)
    nonebot.load_plugins("bot")
    # 支持通过环境变量覆盖监听地址和端口，默认监听 0.0.0.0:8080
    host = os.getenv("NB_HOST", "0.0.0.0")
    port = int(os.getenv("NB_PORT", "8080"))
    # 使用 NoneBot 的内置运行方式
    nonebot.run(host=host, port=port)
