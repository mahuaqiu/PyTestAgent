# app/executor/pytest_runner.py
"""
pytest 执行器
- 构建执行命令
- 异步执行 pytest 测试
- 解析执行结果
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from app.config import config
from app.utils.logger import logger


class PytestRunner:
    """pytest 执行器"""

    def __init__(self):
        self.testcase_timeout = config.testcase_timeout

    def _build_command(
        self,
        test_path: Path,
        exe_param: Dict
    ) -> List[str]:
        """构建 pytest 执行命令"""
        cmd = ['pytest', str(test_path)]

        # 传递 exeParam
        exe_param_json = json.dumps(exe_param, ensure_ascii=False)
        cmd.append(f'--exeParam={exe_param_json}')

        return cmd

    async def run_testcase(
        self,
        repo_path: Path,
        svn_script_path: str,
        testcase_name: str,
        exe_param: Dict,
        execution_id: str
    ) -> Tuple[bool, Dict]:
        """
        异步执行单个测试用例
        每个用例在独立进程中执行，互不影响

        Args:
            repo_path: 仓库路径
            svn_script_path: 测试脚本路径
            testcase_name: 用例名称
            exe_param: 执行参数
            execution_id: 执行ID（用于日志追踪）

        Returns: (成功标志, 结果信息)
        """
        # 拼接完整路径
        test_path = repo_path / svn_script_path

        if not test_path.exists():
            logger.error(f"[{execution_id}] 测试文件不存在: {test_path}")
            return False, {
                'success': False,
                'error': '测试文件不存在',
                'begin_time': int(datetime.now().timestamp() * 1000),
                'end_time': int(datetime.now().timestamp() * 1000)
            }

        logger.info(f"[{execution_id}] 开始执行测试: {test_path}")

        # 构建命令
        cmd = self._build_command(test_path, exe_param)
        logger.debug(f"[{execution_id}] 执行命令: {' '.join(cmd)}")

        # 记录开始时间
        begin_time = datetime.now()
        begin_timestamp = int(begin_time.timestamp() * 1000)

        try:
            # 异步执行 pytest（使用 asyncio.create_subprocess_exec）
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 等待执行完成（带超时控制）
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.testcase_timeout
            )

            end_time = datetime.now()
            end_timestamp = int(end_time.timestamp() * 1000)

            # 判断执行结果
            success = process.returncode == 0

            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')

            logger.info(f"[{execution_id}] 测试执行完成: {testcase_name}, 结果: {'成功' if success else '失败'}")

            # 逐行输出 pytest 日志（带 execution_id 标识，便于 grep）
            if stderr_text:
                for line in stderr_text.strip().split('\n'):
                    if line.strip():
                        logger.info(f"[{execution_id}] {line}")

            if stdout_text:
                for line in stdout_text.strip().split('\n'):
                    if line.strip():
                        logger.debug(f"[{execution_id}] {line}")

            return True, {
                'success': success,
                'begin_time': begin_timestamp,
                'end_time': end_timestamp,
                'output': stdout_text + stderr_text,
                'returncode': process.returncode
            }

        except asyncio.TimeoutError:
            end_time = datetime.now()
            end_timestamp = int(end_time.timestamp() * 1000)

            # 超时时终止进程
            try:
                process.kill()
                await process.wait()
            except:
                pass

            logger.error(f"[{execution_id}] 测试执行超时: {testcase_name}")
            return False, {
                'success': False,
                'begin_time': begin_timestamp,
                'end_time': end_timestamp,
                'error': '执行超时'
            }
        except Exception as e:
            end_time = datetime.now()
            end_timestamp = int(end_time.timestamp() * 1000)

            logger.error(f"[{execution_id}] 测试执行异常: {testcase_name}, 错误: {e}")
            return False, {
                'success': False,
                'begin_time': begin_timestamp,
                'end_time': end_timestamp,
                'error': str(e)
            }

    def find_report_file(
        self,
        repo_path: Path,
        testcase_number: str
    ) -> Optional[Path]:
        """
        查找测试报告文件
        报告位于 {repo_path}/report/{timestamp}/{number}.html
        并行执行可能生成多个时间戳目录，在最新的几个目录中查找，返回最新的报告文件
        """
        report_dir = repo_path / 'report'

        if not report_dir.exists():
            logger.warning(f"报告目录不存在: {report_dir}")
            return None

        # 查找所有时间戳子目录（格式如 2026_04_06_22_37_05）
        timestamp_dirs = []
        for subdir in report_dir.iterdir():
            if subdir.is_dir():
                try:
                    # 目录名格式: YYYY_MM_DD_HH_MM_SS
                    timestamp = datetime.strptime(subdir.name, '%Y_%m_%d_%H_%M_%S')
                    timestamp_dirs.append((timestamp, subdir))
                except ValueError:
                    continue

        if not timestamp_dirs:
            logger.warning(f"没有找到时间戳目录")
            return None

        # 按时间戳降序排序
        timestamp_dirs.sort(key=lambda x: x[0], reverse=True)

        # 在最新的几个目录中查找 {number}.html，返回最新的
        report_file_name = f'{testcase_number}.html'
        for timestamp, dir_path in timestamp_dirs[:5]:  # 只检查最新的5个目录
            report_file = dir_path / report_file_name
            if report_file.exists():
                logger.info(f"找到报告文件: {report_file}")
                return report_file

        logger.warning(f"报告文件不存在: {report_file_name}")
        return None


# 全局 pytest 执行器实例
pytest_runner = PytestRunner()