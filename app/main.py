# app/main.py
"""
FastAPI 应用入口
- 创建应用
- 注册路由
- 启动时注册和启动定时任务
- 关闭时停止定时任务
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.routes import router
from app.clients.scheduler_client import scheduler_client
from app.utils.scheduler import scheduler_service
from app.utils.logger import logger
from app.config import config
import json


class RawBodyLoggerMiddleware(BaseHTTPMiddleware):
    """捕获原始请求体的中间件，用于调试请求格式"""

    async def dispatch(self, request: Request, call_next):
        # 只记录 POST 请求的 body
        if request.method == "POST":
            try:
                # 读取原始 body
                body_bytes = await request.body()
                body_str = body_bytes.decode('utf-8')

                # 尝试解析 JSON 并记录
                try:
                    body_json = json.loads(body_str)
                    logger.info(f"[RAW_REQUEST] path={request.url.path}, body={json.dumps(body_json, ensure_ascii=False)}")
                except json.JSONDecodeError:
                    logger.warning(f"[RAW_REQUEST] path={request.url.path}, body=非JSON内容: {body_str[:500]}")
            except Exception as e:
                logger.error(f"[RAW_REQUEST_ERROR] 无法读取请求体: {e}")

        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"PyTestAgent 启动: {config.agent_url}")

    # 注册到调度中心
    register_success = await scheduler_client.register()
    if not register_success:
        logger.warning("注册失败，将在下次心跳时重试")

    # 启动定时任务
    scheduler_service.start()

    yield

    # 关闭时
    logger.info("PyTestAgent 关闭")
    scheduler_service.stop()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="PyTestAgent",
        description="测试执行代理服务",
        version=config.agent_version,
        lifespan=lifespan
    )

    # 注册中间件（捕获原始请求体，用于调试）
    app.add_middleware(RawBodyLoggerMiddleware)

    # 注册路由
    app.include_router(router)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.agent_port,
        reload=False
    )