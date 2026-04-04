# app/utils/scheduler.py
"""
定时任务模块
- 心跳上报（每 2 分钟）
- report 清理（每 24 小时）
"""
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import config
from app.clients.scheduler_client import scheduler_client
from app.utils.logger import logger


class SchedulerService:
    """定时任务服务"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def heartbeat_task(self):
        """心跳上报任务"""
        logger.debug("执行心跳上报")
        await scheduler_client.heartbeat()

    async def cleanup_reports_task(self):
        """清理旧报告任务"""
        logger.info("执行报告清理任务")

        work_dir = Path(config.git_work_dir)
        retention_days = config.report_retention_days

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 遍历所有仓库的 report 目录
        if work_dir.exists():
            for repo_dir in work_dir.iterdir():
                if repo_dir.is_dir():
                    report_dir = repo_dir / 'report'
                    if report_dir.exists():
                        # 清理过期 HTML 文件
                        for report_file in report_dir.glob('*.html'):
                            try:
                                file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                                if file_mtime < cutoff_date:
                                    report_file.unlink()
                                    logger.info(f"清理过期报告: {report_file}")
                            except Exception as e:
                                logger.warning(f"清理报告失败: {report_file}, 错误: {e}")

    def start(self):
        """启动定时任务"""
        # 心跳任务（每 2 分钟）
        self.scheduler.add_job(
            self.heartbeat_task,
            'interval',
            minutes=config.heartbeat_interval // 60,
            id='heartbeat'
        )

        # 报告清理任务（每 24 小时）
        self.scheduler.add_job(
            self.cleanup_reports_task,
            'interval',
            hours=config.report_cleanup_interval // 3600,
            id='cleanup_reports'
        )

        self.scheduler.start()
        logger.info("定时任务已启动")

    def stop(self):
        """停止定时任务"""
        self.scheduler.shutdown()
        logger.info("定时任务已停止")


# 全局定时任务服务实例
scheduler_service = SchedulerService()