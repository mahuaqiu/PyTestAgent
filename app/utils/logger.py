# app/utils/logger.py
"""
日志配置模块
- 持久化存储日志
- 文件最大 100M，最多 3 个备份文件
- 记录请求参数、返回结果、异常详细报错行数
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = 'pytest_agent') -> logging.Logger:
    """配置并返回日志记录器"""

    # 日志目录
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / 'pytest_agent.log'

    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 清除已有 handlers
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件 handler（轮转：最大 100M，保留 3 个备份）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 全局 logger 实例
logger = setup_logger()


def log_request(request_id: str, endpoint: str, params):
    """记录请求参数"""
    logger.info(f"[REQUEST] request_id={request_id}, endpoint={endpoint}")
    logger.debug(f"[REQUEST_PARAMS] {params}")


def log_response(request_id: str, endpoint: str, result):
    """记录响应结果"""
    logger.info(f"[RESPONSE] request_id={request_id}, endpoint={endpoint}")
    logger.debug(f"[RESPONSE_RESULT] {result}")


def log_exception(request_id: str, error: Exception, traceback_str: str = None):
    """记录异常详细信息"""
    logger.error(f"[EXCEPTION] request_id={request_id}, error={str(error)}")
    if traceback_str:
        logger.error(f"[TRACEBACK] {traceback_str}")