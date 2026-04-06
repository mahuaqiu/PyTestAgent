# app/api/handlers.py
"""
API 请求处理器
- sendJob: 接收任务，后台异步执行
- stopJob: 停止任务
- closeJob: 关闭任务
"""
import asyncio
import uuid
from fastapi import Request
from app.api.schemas import (
    SendJobRequest, StopJobRequest, CloseJobRequest,
    ApiResponse, ResponseParam
)
from app.executor.task_manager import task_manager
from app.models.task_context import task_context_manager
from app.utils.logger import logger, log_request, log_response


def _get_request_id(header: dict) -> str:
    """从 header 中获取 request_id，兼容多种命名"""
    if not header:
        return uuid.uuid4().hex
    # 支持多种命名方式
    return header.get('requestID') or header.get('request_id') or uuid.uuid4().hex


async def handle_send_job(request: Request, body: SendJobRequest) -> ApiResponse:
    """
    处理 sendJob 请求
    1. 解析参数并记录日志
    2. 立即返回成功响应
    3. 启动后台任务执行
    """
    request_id = _get_request_id(body.header)
    param_dict = body.param or {}

    log_request(request_id, "sendJob", param_dict)

    task_id = param_dict.get('taskID', '')
    logger.info(f"收到任务: task_id={task_id}")

    # 构建响应
    response = ApiResponse(
        param=ResponseParam(status="ok", result=""),
        header={"requestID": request_id}
    )

    log_response(request_id, "sendJob", response.model_dump())

    # 启动后台任务执行（仅当有参数时）
    if param_dict:
        asyncio.create_task(task_manager.execute_job(param_dict))

    return response


async def handle_stop_job(request: Request, body: StopJobRequest) -> ApiResponse:
    """
    处理 stopJob 请求
    1. 设置停止标志
    2. 立即返回成功响应
    """
    request_id = _get_request_id(body.header)

    param_dict = body.param or {}
    log_request(request_id, "stopJob", param_dict)

    # 兼容数字类型的 taskID
    task_id = str(param_dict.get('taskID', '') or '')

    logger.info(f"收到停止请求: task_id={task_id}")

    # 设置停止标志
    if task_id:
        task_manager.stop_current_task(task_id)

    # 构建响应
    response = ApiResponse(
        param=ResponseParam(status="ok", result=""),
        header={"requestID": request_id}
    )

    log_response(request_id, "stopJob", response.model_dump())

    return response


async def handle_close_job(request: Request, body: CloseJobRequest) -> ApiResponse:
    """
    处理 closeJob 请求
    1. 清理任务上下文
    2. 立即返回成功响应
    """
    request_id = _get_request_id(body.header)

    param_dict = body.param or {}
    log_request(request_id, "closeJob", param_dict)

    # 兼容数字类型的 taskID
    task_id = str(param_dict.get('taskID', '') or '')

    logger.info(f"收到关闭请求: task_id={task_id}")

    # 清理上下文
    task_context_manager.clear_context()

    # 构建响应
    response = ApiResponse(
        param=ResponseParam(status="ok", result=""),
        header={"requestID": request_id}
    )

    log_response(request_id, "closeJob", response.model_dump())

    return response