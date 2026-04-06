# app/executor/report_handler.py
"""
报告处理模块
- 上传报告到测试平台
- 构建上报结果数据
- 解析 HTML 报告提取失败信息
"""
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup
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
        testcase_number: str,
        testcase_uri: str,
        exec_result: Dict
    ) -> Dict:
        """
        处理测试报告
        返回上报用的结果数据
        """
        # 查找报告文件
        report_file = pytest_runner.find_report_file(repo_path, testcase_number)

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
            "tcid": testcase_uri  # 使用 testcase.uri 作为 tcid
        }

        return result_data

    async def report_failure(
        self,
        task_id: str,
        task_name: str,
        total_cases: int,
        case_name: str,
        case_round: int,
        repo_path: Path,
        testcase_number: str,
        report_url: Optional[str] = None
    ) -> bool:
        """
        上报失败详情

        Args:
            task_id: 任务ID
            task_name: 任务名称
            total_cases: 用例总数
            case_name: 用例名称
            case_round: 轮次
            repo_path: 仓库路径
            testcase_number: 测试用例编号（用于查找报告）
            report_url: 报告URL

        Returns:
            bool: 上报是否成功
        """
        # 查找并解析 HTML 报告
        report_file = pytest_runner.find_report_file(repo_path, testcase_number)

        if report_file:
            fail_info = self.parse_html_report(report_file)
        else:
            fail_info = {
                "caseFailStep": "",
                "caseFailLog": "",
                "failReason": "HTML日志不存在"
            }

        return await test_platform_client.report_fail(
            task_id=task_id,
            task_name=task_name,
            total_cases=total_cases,
            case_name=case_name,
            case_fail_step=fail_info["caseFailStep"],
            case_fail_log=fail_info["caseFailLog"],
            fail_reason=fail_info["failReason"],
            case_round=case_round,
            log_url=report_url
        )

    def parse_html_report(self, html_path: Path) -> Dict:
        """
        从 HTML 报告提取失败信息

        Args:
            html_path: HTML 报告文件路径

        Returns:
            Dict: {
                "caseFailStep": str,   # 失败步骤名称，多个用逗号分隔
                "caseFailLog": str,    # 失败日志
                "failReason": str      # 失败原因，多个用逗号分隔
            }
        """
        # HTML 不存在
        if not html_path.exists():
            return {
                "caseFailStep": "",
                "caseFailLog": "",
                "failReason": "HTML日志不存在"
            }

        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            # 1. 失败步骤名称
            failed_steps = []
            failed_steps_div = soup.find('div', class_='failed-steps')
            if failed_steps_div:
                steps_list = failed_steps_div.find('ul', class_='failed-steps-list')
                if steps_list:
                    failed_steps = [li.text.strip() for li in steps_list.find_all('li')]

            # 2. 失败原因
            step_errors = soup.find_all('div', class_='step-error')
            error_reasons = [e.text.strip() for e in step_errors]

            # 3. 失败日志
            error_box = soup.find('div', class_='error-box')
            full_error_log = error_box.text.strip() if error_box else ""

            return {
                "caseFailStep": ", ".join(failed_steps),
                "caseFailLog": full_error_log,
                "failReason": ", ".join(error_reasons)
            }
        except Exception as e:
            logger.error(f"HTML 解析异常: {e}")
            return {
                "caseFailStep": "",
                "caseFailLog": "",
                "failReason": "HTML解析失败"
            }


# 全局报告处理器实例
report_handler = ReportHandler()