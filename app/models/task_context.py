# app/models/task_context.py
"""
任务执行上下文模型
- 维护当前任务执行状态
- 支持停止标志设置
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
import threading


@dataclass
class TestCaseInfo:
    """测试用例信息"""
    number: str
    name: str
    svn_script_path: str
    schedule_block_id: str
    exe_platform: str = "PyTestAgent"
    uri: str = ""  # 用例唯一标识，用于上报 tcid


@dataclass
class TaskContext:
    """任务执行上下文"""
    task_id: str
    task_project_id: str
    task_project_name: str
    testcase_block_id: str
    scheduler_block_id: str
    run_round: str
    task_type: str  # 4串行, 5并行
    git_url: str
    branch: str = "master"
    exe_param: Dict = field(default_factory=dict)
    testcases: List[TestCaseInfo] = field(default_factory=list)
    group_id: str = ""  # 用于上传报告时的 tepID

    # 执行状态
    stop_requested: bool = False
    current_testcase_index: int = 0
    start_time: Optional[datetime] = None

    # 注册返回的 agent_id
    agent_id: Optional[str] = None

    # 线程锁
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def request_stop(self):
        """请求停止任务"""
        with self._lock:
            self.stop_requested = True

    def is_stop_requested(self) -> bool:
        """检查是否请求停止"""
        with self._lock:
            return self.stop_requested

    def update_index(self, index: int):
        """更新当前用例索引"""
        with self._lock:
            self.current_testcase_index = index


class TaskContextManager:
    """任务上下文管理器"""

    _instance = None
    _lock = threading.Lock()
    _current_context: Optional[TaskContext] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def set_context(self, context: TaskContext):
        """设置当前任务上下文"""
        with self._lock:
            self._current_context = context

    def get_context(self) -> Optional[TaskContext]:
        """获取当前任务上下文"""
        with self._lock:
            return self._current_context

    def clear_context(self):
        """清除当前任务上下文"""
        with self._lock:
            self._current_context = None

    def is_busy(self) -> bool:
        """检查是否有任务正在执行"""
        with self._lock:
            return self._current_context is not None


# 全局任务上下文管理器
task_context_manager = TaskContextManager()