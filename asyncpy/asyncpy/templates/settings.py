# -*- coding: utf-8 -*-



"""
CREATE YOUR DEFAULT_CONFIG !

Some configuration:
        CONCURRENT_REQUESTS     并发数量
        RETRIES                 重试次数
        DOWNLOAD_DELAY          下载延时
        RETRY_DELAY             重试延时
        DOWNLOAD_TIMEOUT        超时限制
        CLOSESPIDER_TIMEOUT     定时关闭
        USER_AGENT              用户代理
        LOG_FILE                日志路径
        LOG_LEVEL               日志等级
"""


CONCURRENT_REQUESTS = 20





MIDDLEWARE = [
# 'middlewares.middleware',
            ]


# PIPELINES = []




DEFAULT_REQUEST_CONFIG = {
    "RETRIES": 0,
    "DOWNLOAD_DELAY": 0,
    "RETRY_DELAY": 0,
    "DOWNLOAD_TIMEOUT": 10,
}


# '''生成日志文件'''
# LOG_FILE = './asyncpy.log'
# LOG_LEVEL = 'DEBUG'



# CLOSESPIDER_TIMEOUT = 10




#USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36"