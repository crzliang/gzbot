"""
CTF机器人主模块
集成所有功能模块，提供统一的入口点
"""

# 导入所有功能模块
from . import commands  # 命令处理模块
from . import notifications  # 通知系统模块

# 所有功能已通过模块导入自动初始化
# - commands 模块提供 /gc 和 /rank 命令
# - notifications 模块提供自动通知播报功能
