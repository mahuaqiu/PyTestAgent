# app/executor/report_handler.py
"""
报告处理模块
- 上传报告到测试平台
- 构建上报结果数据
"""
from pathlib import Path
from typing import Dict, Optional
from app.clients.test_platform_client import test_platform_client
from app.executor.pytest_runner import pytest_runner
from app.utils.logger import logger


class ReportHandler:
    """报告处理器"""

    async def process_report(
        self,
        task_id: str,
        case_round: int,
        repo_path: Path,
        testcase_name: str,
        exec_result: Dict
    ) -> Dict:
        """
        处理测试报告
        返回上报用的结果数据
        """
        # 查找报告文件
        report_file = pytest_runner.find_report_file(repo_path, testcase_name)

        report_url = ""

        # 上传报告
        if report_file:
            report_url = await test_platform_client.upload_report(
                task_id=task_id,
                case_round=case_round,
                report_file=report_file
            )
            if report_url:
                logger.info(f"报告上传成功: {report_url}")
            else:
                logger.warning("报告上传失败")

        # 构建上报结果
        # Result: 0成功 1失败 2部分失败 3执行机不可用 4阻塞
        result_code = "0" if exec_result.get('success') else "1"

        result_data = {
            "BeginTime": str(exec_result.get('begin_time', '')),
            "EndTime": str(exec_result.get('end_time', '')),
            "FailureCauseType": "",
            "Result": result_code,
            "errorReason": "",
            "failureCause": exec_result.get('error', '')[:1024] if not exec_result.get('success') else "",
            "caseLogUrl": report_url[:255] if report_url else "",
            "tcid": testcase_name  # 对应 svnScriptPath 作为 tcid
        }

        return result_data

    async def report_failure(
        self,
        task_id: str,
        task_name: str,
        total_cases: int,
        case_name: str,
        case_round: int,
        exec_result: Dict,
        report_url: Optional[str] = None
    ) -> bool:
        """上报失败详情"""
        # 提取失败步骤和日志
        fail_step = ""
        fail_log = exec_result.get('error', '')[:1024] if exec_result.get('error') else exec_result.get('output', '')[:1024]

        return await test_platform_client.report_fail(
            task_id=task_id,
            task_name=task_name,
            total_cases=total_cases,
            case_name=case_name,
            case_fail_step=fail_step,
            case_fail_log=fail_log,
            case_round=case_round,
            log_url=report_url
        )


# 全局报告处理器实例
report_handler = ReportHandler()