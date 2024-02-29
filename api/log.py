import datetime
import logging
import os


# 创建格式器
class LogFormatter(logging.Formatter):
    # 处理消息中的换行，替换为空格
    def format(self, record):
        record.msg = record.msg.replace('\n', ' ')
        return super().format(record)


# 创建一个logger实例并设置日志级别
logger = logging.getLogger('branch-manage')
logger.setLevel(logging.DEBUG)

# 配置formatter
formatter = LogFormatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# 配置handler，拟将日志记录输出在控制台
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置handler，拟将日志记录输出至文件
cur_time = datetime.datetime.now()
file_dir = "/data/logs/"
if not os.path.exists(file_dir):
    file_dir = ""
file_name = "{}branch-manage-{}.log".format(file_dir, cur_time.strftime('%Y%m%d'))
file_handler = logging.FileHandler(file_name)
file_handler.setFormatter(formatter)

# 添加handler至logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
