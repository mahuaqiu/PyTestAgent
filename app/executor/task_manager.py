# app/executor/task_manager.py
"""
任务执行管理器
- 解析任务参数
- 串行/并行调度
- 协调各模块执行
"""
import asyncio
import json
from typing import Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from app.config import config
from app.models.task_context import TaskContext, TestCaseInfo, TaskContextManager
from app.git_ops.repo_manager import repo_manager
from app.executor.pytest_runner import pytest_runner
from app.executor.report_handler import report_handler
from app.clients.scheduler_client import scheduler_client
from app.utils.logger import logger


class TaskManager:
    """任务执行管理器"""

    def __init__(self):
        self.context_manager = TaskContextManager()
        self.executor = ThreadPoolExecutor(max_workers=config.max_parallel)

    def _parse_job_params(self, param: Dict) -> TaskContext:
        """解析任务参数"""
        # 直接使用 param，适配调度中心的单层结构
        inner_param = param

        # 解析 userExtendContent
        user_extend_content = inner_param.get('userExtendContent', '{}')
        try:
            extend_data = json.loads(user_extend_content)
        except:
            extend_data = {}

        git_url = extend_data.get('git_url', '')

        # 解析 exeParam
        exe_param_str = extend_data.get('exeParam', '{}')
        try:
            exe_param = json.loads(exe_param_str)
        except:
            exe_param = {}

        branch = exe_param.get('branch', config.git_default_branch)

        # 解析 testcase 列表（字段可能是数字或字符串，统一转字符串）
        testcase_list = inner_param.get('testcase', [])
        testcases = []
        for tc in testcase_list:
            testcases.append(TestCaseInfo(
                number=str(tc.get('number', '')),
                name=str(tc.get('name', '')),
                svn_script_path=str(tc.get('svnScriptPath', '')),
                schedule_block_id=str(tc.get('scheduleBlockId', '')),
                exe_platform=str(tc.get('exeplatform', 'PyTestAgent')),
                uri=str(tc.get('uri', ''))  # 用例唯一标识
            ))

        # 创建任务上下文（字段可能是数字或字符串，统一转字符串）
        context = TaskContext(
            task_id=str(inner_param.get('taskID', '')),
            task_project_id=str(inner_param.get('taskProjectID', '')),
            task_project_name=str(inner_param.get('taskProjectName', '')),
            testcase_block_id=str(inner_param.get('testcaseBlockID', '')),
            scheduler_block_id=str(inner_param.get('schedulerBlockID', '')),
            run_round=str(inner_param.get('runRound', '1')),
            task_type=str(inner_param.get('taskType', '4') or '4'),  # taskType 可能是空字符串
            git_url=git_url,
            branch=branch,
            exe_param=exe_param,
            testcases=testcases,
            group_id=str(inner_param.get('groupId', config.agent_group_id))  # 用于上传报告
        )

        return context

    async def execute_job(self, param: Dict):
        """执行任务（后台异步）"""
        # 解析参数
        context = self._parse_job_params(param)
        context.start_time = datetime.now()

        # 设置当前任务上下文
        self.context_manager.set_context(context)

        logger.info(f"开始执行任务: task_id={context.task_id}, 用例数={len(context.testcases)}")

        try:
            # 准备仓库
            success, repo_path, error = repo_manager.prepare_repo(
                context.git_url,
                param.get('userExtendContent', '{}')
            )

            if not success:
                logger.error(f"仓库准备失败: {error}")
                # 直接上报完成（失败）
                await self._complete_task(context, success=False)
                return

            # 判断执行模式
            is_parallel = context.task_type == '5'

            logger.info(f"执行模式: {'并行' if is_parallel else '串行'}")

            # 执行测试用例
            if is_parallel:
                await self._execute_parallel(context, repo_path)
            else:
                await self._execute_serial(context, repo_path)

            # 任务完成
            await self._complete_task(context)

        except Exception as e:
            logger.error(f"任务执行异常: {e}")
            await self._complete_task(context, success=False)
        finally:
            # 清理上下文
            self.context_manager.clear_context()

    async def _execute_serial(self, context: TaskContext, repo_path):
        """串行执行"""
        for i, testcase in enumerate(context.testcases):
            # 检查停止请求
            if context.is_stop_requested():
                logger.info(f"收到停止请求，跳过剩余用例，当前索引={i}")
                break

            context.update_index(i)

            # 执行用例
            await self._execute_single_testcase(context, testcase, repo_path, i)

    async def _execute_parallel(self, context: TaskContext, repo_path):
        """并行执行（最多 max_parallel 条）"""
        tasks = []
        semaphore = asyncio.Semaphore(config.max_parallel)

        async def run_with_semaphore(index: int, testcase: TestCaseInfo):
            async with semaphore:
                if context.is_stop_requested():
                    logger.info(f"收到停止请求，跳过用例 index={index}")
                    return
                await self._execute_single_testcase(context, testcase, repo_path, index)

        for i, testcase in enumerate(context.testcases):
            tasks.append(run_with_semaphore(i, testcase))

        await asyncio.gather(*tasks)

    async def _execute_single_testcase(
        self,
        context: TaskContext,
        testcase: TestCaseInfo,
        repo_path,
        index: int
    ):
        """执行单个用例并上报"""
        logger.info(f"执行用例 [{index}]: {testcase.name}")

        # 执行测试
        is_parallel = context.task_type == '5'
        success, exec_result = pytest_runner.run_testcase(
            repo_path=repo_path,
            svn_script_path=testcase.svn_script_path,
            testcase_name=testcase.name,
            exe_param=context.exe_param,
            parallel=is_parallel and len(context.testcases) > 1
        )

        # 处理报告和上报
        result_data = await report_handler.process_report(
            task_id=context.task_id,
            case_round=int(context.run_round),
            repo_path=repo_path,
            testcase_name=testcase.name,
            testcase_uri=testcase.uri,  # 使用 testcase.uri 作为 tcid
            group_id=context.group_id,  # groupId 作为 tepID
            exec_result=exec_result
        )

        # 失败时上报到测试平台
        if not exec_result.get('success'):
            await report_handler.report_failure(
                task_id=context.task_id,
                task_name=context.task_project_name,
                total_cases=len(context.testcases),
                case_name=testcase.name,
                case_round=int(context.run_round),
                repo_path=repo_path,
                testcase_name=testcase.name,
                report_url=result_data.get('caseLogUrl')
            )

        # 上报结果到调度中心
        await scheduler_client.report(
            testcase_block_id=context.testcase_block_id,
            round=context.run_round,
            results=[result_data]
        )

    async def _complete_task(self, context: TaskContext, success: bool = True):
        """任务完成处理"""
        logger.info(f"任务完成处理: task_id={context.task_id}")

        # 等待 10 秒
        await asyncio.sleep(10)

        # 上报 complete（失败重试一次）
        complete_success = await scheduler_client.complete(
            task_id=context.task_id,
            scheduler_block_id=context.scheduler_block_id,
            round=context.run_round,
            testcase_block_id=context.testcase_block_id
        )

        if not complete_success:
            logger.warning("complete 上报失败，重试一次")
            await asyncio.sleep(2)
            await scheduler_client.complete(
                task_id=context.task_id,
                scheduler_block_id=context.scheduler_block_id,
                round=context.run_round,
                testcase_block_id=context.testcase_block_id
            )

    def stop_current_task(self, task_id: str) -> bool:
        """停止当前任务"""
        context = self.context_manager.get_context()
        if context and context.task_id == task_id:
            context.request_stop()
            logger.info(f"设置停止标志: task_id={task_id}")
            return True
        return False


# 全局任务管理器实例
task_manager = TaskManager()