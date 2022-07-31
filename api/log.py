import logging

# 创建一个logger实例并设置日志级别
logger = logging.getLogger('bot')
logger.setLevel(logging.DEBUG)

# 配置handler，拟将日志记录输出在控制台
stdout_handler = logging.StreamHandler()

# 配置formatter
formatter = logging.Formatter('%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s')
stdout_handler.setFormatter(formatter)

# 添加handler至logger
logger.addHandler(stdout_handler)