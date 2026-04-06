# app/clients/test_platform_client.py
"""
测试平台接口客户端
- fail: 用例失败上报
- upload: 报告文件上传

响应模型结构:
{
    "message": "操作结果信息",
    "data": { ... }  # 可选，如上传后的访问URL
}
"""
import httpx
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from app.config import config
from app.utils.logger import logger, log_request, log_response, log_exception


class TestPlatformClient:
    """测试平台客户端"""

    def __init__(self):
        self.base_url = config.test_platform_base_url

    def _generate_request_id(self) -> str:
        """生成随机请求ID"""
        return uuid.uuid4().hex

    async def _request_with_retry(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        max_retries: int = 1
    ) -> Optional[Dict]:
        """带重试的请求"""
        request_id = self._generate_request_id()
        url = f"{self.base_url}{endpoint}"

        log_request(request_id, endpoint, data or files)

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60, verify=False, trust_env=False) as client:
                    if files:
                        # FormData 上传
                        response = await client.post(url, data=data, files=files)
                    else:
                        # JSON 请求
                        response = await client.post(url, json=data)

                    result = response.json()
                    log_response(request_id, endpoint, result)
                    return result
            except Exception as e:
                logger.warning(f"请求失败 (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2)
                else:
                    log_exception(request_id, e)
                    return None

    async def report_fail(
        self,
        task_id: str,
        task_name: str,
        total_cases: int,
        case_name: str,
        case_fail_step: str,
        case_fail_log: str,
        fail_reason: str,
        case_round: int,
        log_url: Optional[str] = None
    ) -> bool:
        """
        上报用例失败

        Args:
            task_id: 任务ID
            task_name: 任务名称
            total_cases: 用例总数
            case_name: 用例名称
            case_fail_step: 失败步骤
            case_fail_log: 失败日志
            fail_reason: 失败原因
            case_round: 轮次
            log_url: 报告URL

        Returns:
            bool: 上报是否成功
        """
        data = {
            "taskId": task_id,
            "taskName": task_name,
            "totalCases": total_cases,
            "caseName": case_name,
            "caseFailStep": case_fail_step,
            "caseFailLog": case_fail_log,
            "failReason": fail_reason,
            "caseRound": case_round,
            "logUrl": log_url or "",
            "failTime": datetime.now().isoformat()
        }

        result = await self._request_with_retry("/api/core/test-report/fail", data)

        if result and "成功" in result.get("message", ""):
            logger.info("失败上报成功")
            return True

        logger.warning("失败上报失败")
        return False

    async def upload_report(
        self,
        task_id: str,
        case_round: int,
        report_file: Path
    ) -> Optional[str]:
        """上传报告文件，返回报告URL"""
        if not report_file.exists():
            logger.warning(f"报告文件不存在: {report_file}")
            return None

        # 准备 FormData
        data = {
            "task_id": task_id,
            "case_round": case_round
        }

        with open(report_file, 'rb') as f:
            files = {
                "file": (report_file.name, f, 'text/html')
            }

            try:
                result = await self._request_with_retry(
                    "/api/core/test-report/upload",
                    data=data,
                    files=files
                )

                if result and "成功" in result.get("message", ""):
                    url = result.get("data", {}).get("url")
                    logger.info(f"报告上传成功，url={url}")
                    return url

                logger.warning("报告上传失败")
                return None
            except Exception as e:
                logger.error(f"报告上传异常: {e}")
                return None


# 全局客户端实例
test_platform_client = TestPlatformClient()