# app/main.py
"""
FastAPI 应用入口
- 创建应用
- 注册路由
- 启动时注册和启动定时任务
- 关闭时停止定时任务
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.clients.scheduler_client import scheduler_client
from app.utils.scheduler import scheduler_service
from app.utils.logger import logger
from app.config import config


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