# app/executor/pytest_runner.py
"""
pytest 执行器
- 构建执行命令
- 执行 pytest 测试
- 解析执行结果
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from app.config import config
from app.utils.logger import logger


class PytestRunner:
    """pytest 执行器"""

    def __init__(self):
        self.max_parallel = config.max_parallel
        self.testcase_timeout = config.testcase_timeout

    def _build_command(
        self,
        test_path: Path,
        exe_param: Dict,
        parallel: bool = False
    ) -> List[str]:
        """构建 pytest 执行命令"""
        cmd = ['pytest', str(test_path)]

        # 传递 exeParam
        exe_param_json = json.dumps(exe_param, ensure_ascii=False)
        cmd.append(f'--exeParam={exe_param_json}')

        # 并行模式
        if parallel:
            cmd.extend(['-n', str(self.max_parallel)])

        return cmd

    def run_testcase(
        self,
        repo_path: Path,
        svn_script_path: str,
        testcase_name: str,
        exe_param: Dict,
        parallel: bool = False
    ) -> Tuple[bool, Dict]:
        """
        执行单个测试用例
        返回: (成功标志, 结果信息)
        """
        # 拼接完整路径
        test_path = repo_path / svn_script_path

        if not test_path.exists():
            logger.error(f"测试文件不存在: {test_path}")
            return False, {
                'success': False,
                'error': '测试文件不存在',
                'begin_time': int(datetime.now().timestamp() * 1000),
                'end_time': int(datetime.now().timestamp() * 1000)
            }

        logger.info(f"开始执行测试: {test_path}")

        # 构建命令
        cmd = self._build_command(test_path, exe_param, parallel)
        logger.debug(f"执行命令: {cmd}")

        # 记录开始时间
        begin_time = datetime.now()
        begin_timestamp = int(begin_time.timestamp() * 1000)

        try:
            # 执行 pytest
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.testcase_timeout  # 可配置超时时间
            )

            end_time = datetime.now()
            end_timestamp = int(end_time.timestamp() * 1000)

            # 判断执行结果
            success = result.returncode == 0

            output = result.stdout + result.stderr

            logger.info(f"测试执行完成: {testcase_name}, 结果: {'成功' if success else '失败'}")
            logger.debug(f"执行输出: {output[:500]}")

            return True, {
                'success': success,
                'begin_time': begin_timestamp,
                'end_time': end_timestamp,
                'output': output,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            end_timestamp = int(end_time.timestamp() * 1000)

            logger.error(f"测试执行超时: {testcase_name}")
            return False, {
                'success': False,
                'begin_time': begin_timestamp,
                'end_time': end_timestamp,
                'error': '执行超时'
            }
        except Exception as e:
            end_time = datetime.now()
            end_timestamp = int(end_time.timestamp() * 1000)

            logger.error(f"测试执行异常: {testcase_name}, 错误: {e}")
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