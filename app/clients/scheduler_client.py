# app/clients/scheduler_client.py
"""
调度中心接口客户端
- register: 启动时注册
- heartbeat: 心跳上报
- report: 用例结果上报
- complete: 任务完成上报
"""
import httpx
import uuid
import asyncio
from typing import Dict, List, Optional, Any
from app.config import config
from app.utils.logger import logger, log_request, log_response, log_exception


class SchedulerClient:
    """调度中心客户端"""

    def __init__(self):
        self.base_url = config.scheduler_base_url
        self.agent_id: Optional[str] = None

    def _generate_request_id(self) -> str:
        """生成随机请求ID"""
        return uuid.uuid4().hex

    def _get_headers(self, request_id: str) -> Dict[str, str]:
        """获取请求头"""
        return {
            "request_id": request_id,
            "Content-type": "application/json;charset=utf-8"
        }

    async def _request_with_retry(
        self,
        endpoint: str,
        data: Any,
        max_retries: int = 1
    ) -> Optional[Dict]:
        """带重试的请求"""
        request_id = self._generate_request_id()
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(request_id)

        log_request(request_id, endpoint, data)

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(url, json=data, headers=headers)
                    result = response.json()
                    log_response(request_id, endpoint, result)
                    return result
            except Exception as e:
                logger.warning(f"请求失败 (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    # 等待 2 秒后重试
                    await asyncio.sleep(2)
                else:
                    log_exception(request_id, e)
                    return None

    async def register(self) -> bool:
        """向调度中心注册"""
        data = [{
            "groupId": config.agent_group_id,
            "rgId": config.rg_id,
            "name": config.agent_group_id,
            "type": "PyTestAgent",
            "status": "idle",
            "workspacdId": "PyTestAgent",
            "url": config.agent_url,
            "version": config.agent_version,
            "productId": config.product_id,
            "author": config.agent_author,
            "share": 0
        }]

        result = await self._request_with_retry("/register", data)

        if result and result.get("status") == "ok":
            # 保存返回的 agent_id
            agents = result.get("result", [])
            if agents and len(agents) > 0:
                self.agent_id = agents[0].get("id")
            logger.info(f"注册成功，agent_id={self.agent_id}")
            return True

        logger.error("注册失败")
        return False

    async def heartbeat(self) -> bool:
        """心跳上报"""
        if not self.agent_id:
            logger.warning("未注册，跳过心跳")
            return False

        data = [self.agent_id]
        result = await self._request_with_retry("/heartbeat", data)

        if result and result.get("status") == "ok":
            logger.debug("心跳上报成功")
            return True

        logger.warning("心跳上报失败")
        return False

    async def report(
        self,
        testcase_block_id: str,
        round: str,
        results: List[Dict]
    ) -> bool:
        """上报用例执行结果"""
        data = {
            "param": {
                "result": "executing",
                "results": results,
                "round": round,
                "testcaseBlockID": testcase_block_id,
                "realTepIp": ""
            }
        }

        result = await self._request_with_retry("/report", data)

        if result and result.get("status") == "ok":
            logger.info("用例结果上报成功")
            return True

        logger.warning("用例结果上报失败")
        return False

    async def complete(
        self,
        task_id: str,
        scheduler_block_id: str,
        round: str,
        testcase_block_id: str
    ) -> bool:
        """任务完成上报"""
        data = {
            "taskID": task_id,
            "schedulerID": scheduler_block_id,
            "round": int(round),
            "tcBlockID": testcase_block_id,
            "groupId": config.agent_group_id,
            "result": "complete",
            "exceptionReason": ""
        }

        result = await self._request_with_retry("/complete", data)

        if result and result.get("status") == "ok":
            logger.info("任务完成上报成功")
            return True

        logger.warning("任务完成上报失败")
        return False


# 全局客户端实例
scheduler_client = SchedulerClient()