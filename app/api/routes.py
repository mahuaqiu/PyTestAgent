# app/api/routes.py
"""
API 路由定义
"""
from fastapi import APIRouter, Request
from app.api.schemas import SendJobRequest, StopJobRequest, CloseJobRequest, ApiResponse
from app.api.handlers import handle_send_job, handle_stop_job, handle_close_job


router = APIRouter()


@router.post("/sendJob", response_model=ApiResponse)
async def send_job(request: Request, body: SendJobRequest):
    """接收任务接口"""
    return await handle_send_job(request, body)


@router.post("/stopJob", response_model=ApiResponse)
async def stop_job(request: Request, body: StopJobRequest):
    """停止任务接口"""
    return await handle_stop_job(request, body)


@router.post("/closeJob", response_model=ApiResponse)
async def close_job(request: Request, body: CloseJobRequest):
    """关闭任务接口"""
    return await handle_close_job(request, body)