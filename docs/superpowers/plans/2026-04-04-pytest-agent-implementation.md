# PyTestAgent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个基于 FastAPI + Docker 的测试执行代理服务，接受调度中心调度，执行 pytest 用例并上报结果。

**Architecture:** 模块化分层架构，分为 API 层、任务执行层、Git 操作层、客户端层和工具层，各模块职责清晰、接口明确。

**Tech Stack:** FastAPI, uvicorn, pytest, pytest-xdist, pytest-html, httpx, pyyaml, apscheduler

---

## 文件结构

### 新建文件清单

| 文件 | 职责 |
|------|------|
| `requirements.txt` | Python 依赖声明 |
| `config.yaml` | 默认配置文件 |
| `.env.example` | 环境变量示例 |
| `app/__init__.py` | 应用包初始化 |
| `app/config.py` | 配置管理（环境变量优先） |
| `app/main.py` | FastAPI 应用入口 |
| `app/api/__init__.py` | API 包初始化 |
| `app/api/schemas.py` | 请求/响应 Pydantic 模型 |
| `app/api/handlers.py` | 请求处理器 |
| `app/api/routes.py` | API 路由定义 |
| `app/executor/__init__.py` | 执行器包初始化 |
| `app/executor/pytest_runner.py` | pytest 执行器 |
| `app/executor/report_handler.py` | 报告处理和上传 |
| `app/executor/task_manager.py` | 任务执行管理（串行/并行调度） |
| `app/git_ops/__init__.py` | Git 操作包初始化 |
| `app/git_ops/repo_manager.py` | Git 仓库操作 |
| `app/clients/__init__.py` | 客户端包初始化 |
| `app/clients/scheduler_client.py` | 调度中心接口客户端 |
| `app/clients/test_platform_client.py` | 测试平台接口客户端 |
| `app/utils/__init__.py` | 工具包初始化 |
| `app/utils/logger.py` | 日志配置（100M/3文件轮转） |
| `app/utils/scheduler.py` | 定时任务（心跳、report清理） |
| `app/models/__init__.py` | 模型包初始化 |
| `app/models/task_context.py` | 任务执行上下文模型 |
| `Dockerfile` | Docker 构建文件 |
| `docker-compose.yaml` | Docker Compose 配置 |

---

## Task 1: 项目初始化

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `.env.example`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi>=0.100.0
uvicorn>=0.23.0
pytest>=7.0.0
pytest-xdist>=3.0.0
pytest-html>=3.0.0
pyyaml>=6.0
httpx>=0.24.0
apscheduler>=3.10.0
```

- [ ] **Step 2: 创建 config.yaml**

```yaml
agent:
  ip: "192.168.0.100"
  port: 5000
  version: "1.0"
  author: "mahuqiu"

scheduler:
  base_url: "http://scheduler-center:8080"

test_platform:
  base_url: "http://test-platform:8000"

git:
  work_dir: "/home"
  default_branch: "master"

execution:
  max_parallel: 3

registration:
  rg_id: ""
  product_id: ""

heartbeat:
  interval: 120

report_cleanup:
  interval: 86400
  retention_days: 7
```

- [ ] **Step 3: 创建 .env.example**

```bash
AGENT__IP=192.168.0.100
AGENT__PORT=5000
SCHEDULER__BASE_URL=http://scheduler-center:8080
TEST_PLATFORM__BASE_URL=http://test-platform:8000
REGISTRATION__RG_ID=your_rg_id
REGISTRATION__PRODUCT_ID=your_product_id
EXECUTION__MAX_PARALLEL=3
```

- [ ] **Step 4: 创建应用目录结构**

```bash
mkdir -p app/api app/executor app/git_ops app/clients app/utils app/models logs
```

- [ ] **Step 5: 创建各包的 __init__.py**

创建空文件：
- `app/__init__.py`
- `app/api/__init__.py`
- `app/executor/__init__.py`
- `app/git_ops/__init__.py`
- `app/clients/__init__.py`
- `app/utils/__init__.py`
- `app/models/__init__.py`

- [ ] **Step 6: 提交初始化文件**

```bash
git add requirements.txt config.yaml .env.example app/ logs/
git commit -m "初始化项目结构和配置文件"
```

---

## Task 2: 配置管理模块

**Files:**
- Create: `app/config.py`

- [ ] **Step 1: 创建配置管理类**

```python
# app/config.py
"""
配置管理模块
- 从 config.yaml 加载默认配置
- 支持环境变量覆盖（使用 __ 分隔嵌套层级）
"""
import os
import yaml
from pathlib import Path
from typing import Any, Optional


class Config:
    """配置管理类"""
    
    _instance: Optional['Config'] = None
    _config_data: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        else:
            self._config_data = {}
    
    def _get_env_key(self, keys: list) -> str:
        """生成环境变量键名"""
        return '__'.join(k.upper() for k in keys)
    
    def _get_value(self, keys: list) -> Any:
        """递归获取配置值，环境变量优先"""
        env_key = self._get_env_key(keys)
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # 尝试转换类型
            try:
                if env_value.isdigit():
                    return int(env_value)
                return env_value
            except:
                return env_value
        
        # 从 config.yaml 获取
        value = self._config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    @property
    def agent_ip(self) -> str:
        return self._get_value(['agent', 'ip']) or '127.0.0.1'
    
    @property
    def agent_port(self) -> int:
        return self._get_value(['agent', 'port']) or 5000
    
    @property
    def agent_version(self) -> str:
        return self._get_value(['agent', 'version']) or '1.0'
    
    @property
    def agent_author(self) -> str:
        return self._get_value(['agent', 'author']) or 'unknown'
    
    @property
    def scheduler_base_url(self) -> str:
        return self._get_value(['scheduler', 'base_url']) or ''
    
    @property
    def test_platform_base_url(self) -> str:
        return self._get_value(['test_platform', 'base_url']) or ''
    
    @property
    def git_work_dir(self) -> str:
        return self._get_value(['git', 'work_dir']) or '/home'
    
    @property
    def git_default_branch(self) -> str:
        return self._get_value(['git', 'default_branch']) or 'master'
    
    @property
    def max_parallel(self) -> int:
        return self._get_value(['execution', 'max_parallel']) or 3
    
    @property
    def rg_id(self) -> str:
        return self._get_value(['registration', 'rg_id']) or ''
    
    @property
    def product_id(self) -> str:
        return self._get_value(['registration', 'product_id']) or ''
    
    @property
    def heartbeat_interval(self) -> int:
        return self._get_value(['heartbeat', 'interval']) or 120
    
    @property
    def report_cleanup_interval(self) -> int:
        return self._get_value(['report_cleanup', 'interval']) or 86400
    
    @property
    def report_retention_days(self) -> int:
        return self._get_value(['report_cleanup', 'retention_days']) or 7
    
    @property
    def agent_url(self) -> str:
        return f"http://{self.agent_ip}:{self.agent_port}"
    
    @property
    def agent_group_id(self) -> str:
        return f"{self.agent_ip}:{self.agent_port}"


# 全局配置实例
config = Config()
```

- [ ] **Step 2: 提交配置管理模块**

```bash
git add app/config.py
git commit -m "添加配置管理模块（支持环境变量优先覆盖）"
```

---

## Task 3: 日志模块

**Files:**
- Create: `app/utils/logger.py`

- [ ] **Step 1: 创建日志配置模块**

```python
# app/utils/logger.py
"""
日志配置模块
- 持久化存储日志
- 文件最大 100M，最多 3 个备份文件
- 记录请求参数、返回结果、异常详细报错行数
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = 'pytest_agent') -> logging.Logger:
    """配置并返回日志记录器"""
    
    # 日志目录
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'pytest_agent.log'
    
    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 清除已有 handlers
    logger.handlers.clear()
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件 handler（轮转：最大 100M，保留 3 个备份）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# 全局 logger 实例
logger = setup_logger()


def log_request(request_id: str, endpoint: str, params: dict):
    """记录请求参数"""
    logger.info(f"[REQUEST] request_id={request_id}, endpoint={endpoint}")
    logger.debug(f"[REQUEST_PARAMS] {params}")


def log_response(request_id: str, endpoint: str, result: dict):
    """记录响应结果"""
    logger.info(f"[RESPONSE] request_id={request_id}, endpoint={endpoint}")
    logger.debug(f"[RESPONSE_RESULT] {result}")


def log_exception(request_id: str, error: Exception, traceback_str: str = None):
    """记录异常详细信息"""
    logger.error(f"[EXCEPTION] request_id={request_id}, error={str(error)}")
    if traceback_str:
        logger.error(f"[TRACEBACK] {traceback_str}")
```

- [ ] **Step 2: 提交日志模块**

```bash
git add app/utils/logger.py
git commit -m "添加日志配置模块（100M轮转，最多3个备份）"
```

---

## Task 4: 任务上下文模型

**Files:**
- Create: `app/models/task_context.py`

- [ ] **Step 1: 创建任务上下文模型**

```python
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
```

- [ ] **Step 2: 提交任务上下文模型**

```bash
git add app/models/task_context.py
git commit -m "添加任务执行上下文模型和管理器"
```

---

## Task 5: 调度中心客户端

**Files:**
- Create: `app/clients/scheduler_client.py`

- [ ] **Step 1: 创建调度中心客户端**

```python
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
                    import asyncio
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
```

- [ ] **Step 2: 提交调度中心客户端**

```bash
git add app/clients/scheduler_client.py
git commit -m "添加调度中心客户端（register/heartbeat/report/complete）"
```

---

## Task 6: 测试平台客户端

**Files:**
- Create: `app/clients/test_platform_client.py`

- [ ] **Step 1: 创建测试平台客户端**

```python
# app/clients/test_platform_client.py
"""
测试平台接口客户端
- fail: 用例失败上报
- upload: 报告文件上传
"""
import httpx
import uuid
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
                async with httpx.AsyncClient(timeout=60) as client:
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
                    import asyncio
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
        case_round: int,
        log_url: Optional[str] = None
    ) -> bool:
        """上报用例失败"""
        data = {
            "taskId": task_id,
            "taskName": task_name,
            "totalCases": total_cases,
            "caseName": case_name,
            "caseFailStep": case_fail_step,
            "caseFailLog": case_fail_log,
            "caseRound": case_round,
            "logUrl": log_url or "",
            "failTime": datetime.now().isoformat()
        }
        
        result = await self._request_with_retry("/api/core/test-report/fail", data)
        
        if result and result.get("code") == 200:
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
        
        files = {
            "file": (report_file.name, open(report_file, 'rb'), 'text/html')
        }
        
        try:
            result = await self._request_with_retry(
                "/api/core/test-report/upload",
                data=data,
                files=files
            )
            
            if result and result.get("code") == 200:
                url = result.get("data", {}).get("url")
                logger.info(f"报告上传成功，url={url}")
                return url
            
            logger.warning("报告上传失败")
            return None
        finally:
            # 关闭文件
            files["file"][1].close()


# 全局客户端实例
test_platform_client = TestPlatformClient()
```

- [ ] **Step 2: 提交测试平台客户端**

```bash
git add app/clients/test_platform_client.py
git commit -m "添加测试平台客户端（fail上报/report上传）"
```

---

## Task 7: Git 仓库管理

**Files:**
- Create: `app/git_ops/repo_manager.py`

- [ ] **Step 1: 创建 Git 仓库管理模块**

```python
# app/git_ops/repo_manager.py
"""
Git 仓库操作模块
- clone 仓库
- pull 更新
- 分支切换（强制还原本地修改）
"""
import subprocess
import json
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse
from app.config import config
from app.utils.logger import logger


class RepoManager:
    """Git 仓库管理器"""
    
    def __init__(self):
        self.work_dir = Path(config.git_work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_git_command(self, cmd: list, cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """执行 Git 命令"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                logger.error(f"Git 命令失败: {cmd}, 错误: {result.stderr}")
                return False, result.stderr
            return True, result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"Git 命令超时: {cmd}")
            return False, "timeout"
        except Exception as e:
            logger.error(f"Git 命令异常: {cmd}, 错误: {e}")
            return False, str(e)
    
    def _parse_repo_name(self, git_url: str) -> str:
        """从 git_url 解析仓库名"""
        # 处理 HTTPS URL
        if git_url.startswith('https://') or git_url.startswith('http://'):
            parsed = urlparse(git_url)
            path = parsed.path.rstrip('/')
            # 移除 .git 后缀
            if path.endswith('.git'):
                path = path[:-4]
            # 获取最后一部分作为仓库名
            return path.split('/')[-1]
        
        # 处理 SSH URL
        if git_url.startswith('git@'):
            path = git_url.split(':')[-1]
            if path.endswith('.git'):
                path = path[:-4]
            return path.split('/')[-1]
        
        # 默认处理
        return git_url.split('/')[-1].replace('.git', '')
    
    def prepare_repo(
        self,
        git_url: str,
        user_extend_content: str
    ) -> Tuple[bool, Path, str]:
        """
        准备 Git 仓库
        返回: (成功标志, 仓库路径, 错误信息)
        """
        repo_name = self._parse_repo_name(git_url)
        repo_path = self.work_dir / repo_name
        
        logger.info(f"准备仓库: {git_url}, 目标路径: {repo_path}")
        
        # 解析 exeParam 获取分支
        branch = config.git_default_branch
        try:
            extend_data = json.loads(user_extend_content)
            exe_param_str = extend_data.get('exeParam', '{}')
            exe_param = json.loads(exe_param_str)
            branch = exe_param.get('branch', config.git_default_branch)
        except Exception as e:
            logger.warning(f"解析 exeParam 失败: {e}, 使用默认分支")
        
        logger.info(f"目标分支: {branch}")
        
        # 检查仓库是否存在
        if not repo_path.exists():
            # Clone 仓库
            logger.info(f"仓库不存在，开始 clone: {git_url}")
            success, output = self._run_git_command(
                ['git', 'clone', git_url, str(repo_path)]
            )
            if not success:
                return False, repo_path, f"clone 失败: {output}"
        else:
            logger.info(f"仓库已存在: {repo_path}")
        
        # 进入仓库目录
        git_dir = repo_path / '.git'
        if not git_dir.exists():
            return False, repo_path, "仓库目录无效"
        
        # 获取当前分支
        success, current_branch = self._run_git_command(
            ['git', 'branch', '--show-current'],
            cwd=repo_path
        )
        if success:
            current_branch = current_branch.strip()
            logger.info(f"当前分支: {current_branch}")
        
        # 检查是否需要切换分支
        if current_branch != branch:
            logger.info(f"切换分支: {current_branch} -> {branch}")
            
            # 强制还原本地修改
            success, _ = self._run_git_command(
                ['git', 'checkout', '--', '.'],
                cwd=repo_path
            )
            if not success:
                logger.warning("还原本地修改失败（可能没有修改）")
            
            # 切换分支
            success, output = self._run_git_command(
                ['git', 'checkout', branch],
                cwd=repo_path
            )
            if not success:
                # 尝试 fetch 后再切换
                self._run_git_command(['git', 'fetch'], cwd=repo_path)
                success, output = self._run_git_command(
                    ['git', 'checkout', branch],
                    cwd=repo_path
                )
                if not success:
                    return False, repo_path, f"切换分支失败: {output}"
        
        # Pull 更新
        logger.info("执行 git pull")
        success, output = self._run_git_command(
            ['git', 'pull'],
            cwd=repo_path
        )
        if not success:
            logger.warning(f"pull 失败: {output}")
            # 不影响继续执行，可能已经是最新的
        
        logger.info(f"仓库准备完成: {repo_path}")
        return True, repo_path, ""


# 全局仓库管理器实例
repo_manager = RepoManager()
```

- [ ] **Step 2: 提交 Git 仓库管理模块**

```bash
git add app/git_ops/repo_manager.py
git commit -m "添加 Git 仓库管理模块（clone/pull/分支切换）"
```

---

## Task 8: pytest 执行器

**Files:**
- Create: `app/executor/pytest_runner.py`

- [ ] **Step 1: 创建 pytest 执行器**

```python
# app/executor/pytest_runner.py
"""
pytest 执行器
- 构建执行命令
- 执行 pytest 测试
- 解析执行结果
"""
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from app.config import config
from app.utils.logger import logger


class PytestRunner:
    """pytest 执行器"""
    
    def __init__(self):
        self.max_parallel = config.max_parallel
    
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
                'begin_time': datetime.now(),
                'end_time': datetime.now()
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
                timeout=600  # 10分钟超时
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
        testcase_name: str
    ) -> Optional[Path]:
        """
        查找测试报告文件
        报告位于 {repo_path}/report/{testcase_name}.html
        """
        report_dir = repo_path / 'report'
        report_file = report_dir / f'{testcase_name}.html'
        
        if report_file.exists():
            logger.info(f"找到报告文件: {report_file}")
            return report_file
        
        logger.warning(f"报告文件不存在: {report_file}")
        return None


# 全局 pytest 执行器实例
pytest_runner = PytestRunner()
```

- [ ] **Step 2: 提交 pytest 执行器**

```bash
git add app/executor/pytest_runner.py
git commit -m "添加 pytest 执行器（命令构建/执行/结果解析）"
```

---

## Task 9: 报告处理模块

**Files:**
- Create: `app/executor/report_handler.py`

- [ ] **Step 1: 创建报告处理模块**

```python
# app/executor/report_handler.py
"""
报告处理模块
- 上传报告到测试平台
- 构建上报结果数据
"""
from pathlib import Path
from typing import Dict, Optional, List
from app.clients.test_platform_client import test_platform_client
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


# 需要导入 pytest_runner
from app.executor.pytest_runner import pytest_runner

# 全局报告处理器实例
report_handler = ReportHandler()
```

- [ ] **Step 2: 提交报告处理模块**

```bash
git add app/executor/report_handler.py
git commit -m "添加报告处理模块（上传/失败上报）"
```

---

## Task 10: 任务管理器

**Files:**
- Create: `app/executor/task_manager.py`

- [ ] **Step 1: 创建任务管理器**

```python
# app/executor/task_manager.py
"""
任务执行管理器
- 解析任务参数
- 串行/并行调度
- 协调各模块执行
"""
import asyncio
import json
from typing import Dict, List
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
        inner_param = param.get('param', {})
        
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
        
        # 解析 testcase 列表
        testcase_list = inner_param.get('testcase', [])
        testcases = []
        for tc in testcase_list:
            testcases.append(TestCaseInfo(
                number=tc.get('number', ''),
                name=tc.get('name', ''),
                svn_script_path=tc.get('svnScriptPath', ''),
                schedule_block_id=tc.get('scheduleBlockId', ''),
                exe_platform=tc.get('exeplatform', 'PyTestAgent')
            ))
        
        # 创建任务上下文
        context = TaskContext(
            task_id=inner_param.get('taskID', ''),
            task_project_id=inner_param.get('taskProjectID', ''),
            task_project_name=inner_param.get('taskProjectName', ''),
            testcase_block_id=inner_param.get('testcaseBlockID', ''),
            scheduler_block_id=inner_param.get('schedulerBlockID', ''),
            run_round=inner_param.get('runRound', '1'),
            task_type=inner_param.get('taskType', '4'),
            git_url=git_url,
            branch=branch,
            exe_param=exe_param,
            testcases=testcases
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
                param.get('param', {}).get('userExtendContent', '{}')
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
                exec_result=exec_result,
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
```

- [ ] **Step 2: 提交任务管理器**

```bash
git add app/executor/task_manager.py
git commit -m "添加任务执行管理器（串行/并行调度/停止控制）"
```

---

## Task 11: API 数据模型

**Files:**
- Create: `app/api/schemas.py`

- [ ] **Step 1: 创建 API 数据模型**

```python
# app/api/schemas.py
"""
API 请求/响应数据模型
"""
from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class HeaderModel(BaseModel):
    """请求头模型"""
    request_id: str


class TestcaseModel(BaseModel):
    """测试用例模型"""
    number: str
    scheduleBlockId: str
    exeplatform: str
    name: str
    svnScriptPath: str


class JobParamModel(BaseModel):
    """任务参数模型"""
    teps: List[str] = []
    tepType: str = ""
    groupId: str = ""
    taskProjectName: str = ""
    userExtendContent: str = "{}"
    taskType: str = "4"
    testcaseBlockID: str = ""
    taskProjectID: str = ""
    taskID: str = ""
    runRound: str = "1"
    exeplatform: str = "PyTestAgent"
    schedulerBlockID: str = ""
    tcBlockCount: str = "1"
    testcase: List[TestcaseModel] = []


class SendJobRequest(BaseModel):
    """sendJob 请求模型"""
    header: HeaderModel
    param: Dict[str, Any]  # 包含 param 字段


class StopJobParam(BaseModel):
    """stopJob 参数模型"""
    groupId: str
    taskID: str
    schedulerID: str
    tcBlockID: str
    tepUrl: str = ""
    netWork: str = "green"
    envId: str = ""
    option: str = ""
    stopTimeOut: str = "300"
    stopType: str = "later"


class StopJobRequest(BaseModel):
    """stopJob 请求模型"""
    param: StopJobParam


class CloseJobParam(BaseModel):
    """closeJob 参数模型"""
    groupId: str
    taskID: str
    schedulerID: str
    tcBlockID: str


class CloseJobRequest(BaseModel):
    """closeJob 请求模型"""
    param: CloseJobParam


class ResponseParam(BaseModel):
    """响应参数模型"""
    status: str = "ok"
    result: str = ""


class ResponseHeader(BaseModel):
    """响应头模型"""
    request_id: str


class ApiResponse(BaseModel):
    """API 响应模型"""
    param: ResponseParam
    header: ResponseHeader
```

- [ ] **Step 2: 提交 API 数据模型**

```bash
git add app/api/schemas.py
git commit -m "添加 API 请求/响应 Pydantic 数据模型"
```

---

## Task 12: API 处理器

**Files:**
- Create: `app/api/handlers.py`

- [ ] **Step 1: 创建 API 处理器**

```python
# app/api/handlers.py
"""
API 请求处理器
- sendJob: 接收任务，后台异步执行
- stopJob: 停止任务
- closeJob: 关闭任务
"""
import asyncio
import uuid
from typing import Dict
from fastapi import Request
from app.api.schemas import (
    SendJobRequest, StopJobRequest, CloseJobRequest,
    ApiResponse, ResponseParam, ResponseHeader
)
from app.executor.task_manager import task_manager
from app.models.task_context import task_context_manager
from app.utils.logger import logger, log_request, log_response


async def handle_send_job(request: Request, body: SendJobRequest) -> ApiResponse:
    """
    处理 sendJob 请求
    1. 解析参数并记录日志
    2. 立即返回成功响应
    3. 启动后台任务执行
    """
    request_id = body.header.request_id
    
    log_request(request_id, "sendJob", body.param)
    
    logger.info(f"收到任务: task_id={body.param.get('param', {}).get('taskID', '')}")
    
    # 构建响应
    response = ApiResponse(
        param=ResponseParam(status="ok", result=""),
        header=ResponseHeader(request_id=request_id)
    )
    
    log_response(request_id, "sendJob", response.dict())
    
    # 启动后台任务执行
    asyncio.create_task(task_manager.execute_job(body.param))
    
    return response


async def handle_stop_job(request: Request, body: StopJobRequest) -> ApiResponse:
    """
    处理 stopJob 请求
    1. 设置停止标志
    2. 立即返回成功响应
    """
    request_id = request.headers.get('request_id', uuid.uuid4().hex)
    
    log_request(request_id, "stopJob", body.param.dict())
    
    task_id = body.param.taskID
    
    logger.info(f"收到停止请求: task_id={task_id}")
    
    # 设置停止标志
    task_manager.stop_current_task(task_id)
    
    # 构建响应
    response = ApiResponse(
        param=ResponseParam(status="ok", result=""),
        header=ResponseHeader(request_id=request_id)
    )
    
    log_response(request_id, "stopJob", response.dict())
    
    return response


async def handle_close_job(request: Request, body: CloseJobRequest) -> ApiResponse:
    """
    处理 closeJob 请求
    1. 清理任务上下文
    2. 立即返回成功响应
    """
    request_id = request.headers.get('request_id', uuid.uuid4().hex)
    
    log_request(request_id, "closeJob", body.param.dict())
    
    task_id = body.param.taskID
    
    logger.info(f"收到关闭请求: task_id={task_id}")
    
    # 清理上下文
    task_context_manager.clear_context()
    
    # 构建响应
    response = ApiResponse(
        param=ResponseParam(status="ok", result=""),
        header=ResponseHeader(request_id=request_id)
    )
    
    log_response(request_id, "closeJob", response.dict())
    
    return response
```

- [ ] **Step 2: 提交 API 处理器**

```bash
git add app/api/handlers.py
git commit -m "添加 API 处理器（sendJob/stopJob/closeJob）"
```

---

## Task 13: API 路由

**Files:**
- Create: `app/api/routes.py`

- [ ] **Step 1: 创建 API 路由**

```python
# app/api/routes.py
"""
API 路由定义
"""
from fastapi import APIRouter, Request
from app.api.schemas import SendJobRequest, StopJobRequest, CloseJobRequest, ApiResponse
from app.api.handlers import handle_send_job, handle_stop_job, handle_close_job


router = APIRouter()


@router.post("/sendJob", response_model=ApiResponse)
async def send_job(request: Request, body: SendJobRequest):
    """接收任务接口"""
    return await handle_send_job(request, body)


@router.post("/stopJob", response_model=ApiResponse)
async def stop_job(request: Request, body: StopJobRequest):
    """停止任务接口"""
    return await handle_stop_job(request, body)


@router.post("/closeJob", response_model=ApiResponse)
async def close_job(request: Request, body: CloseJobRequest):
    """关闭任务接口"""
    return await handle_close_job(request, body)
```

- [ ] **Step 2: 提交 API 路由**

```bash
git add app/api/routes.py
git commit -m "添加 API 路由定义"
```

---

## Task 14: 定时任务模块

**Files:**
- Create: `app/utils/scheduler.py`

- [ ] **Step 1: 创建定时任务模块**

```python
# app/utils/scheduler.py
"""
定时任务模块
- 心跳上报（每 2 分钟）
- report 清理（每 24 小时）
"""
import asyncio
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
```

- [ ] **Step 2: 提交定时任务模块**

```bash
git add app/utils/scheduler.py
git commit -m "添加定时任务模块（心跳上报/report清理）"
```

---

## Task 15: FastAPI 主入口

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: 创建 FastAPI 主入口**

```python
# app/main.py
"""
FastAPI 应用入口
- 创建应用
- 注册路由
- 启动时注册和启动定时任务
- 关闭时停止定时任务
"""
import asyncio
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
```

- [ ] **Step 2: 提交 FastAPI 主入口**

```bash
git add app/main.py
git commit -m "添加 FastAPI 主入口（生命周期管理）"
```

---

## Task 16: Docker 配置

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yaml`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11.13-slim-bookworm

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY config.yaml .

# 创建工作目录和日志目录
RUN mkdir -p /home /app/logs

# 启动应用
CMD ["python", "-m", "app.main"]
```

- [ ] **Step 2: 创建 docker-compose.yaml**

```yaml
version: "3.8"
services:
  pytest-agent:
    build: .
    ports:
      - "${AGENT__PORT:-5000}:5000"
    environment:
      - AGENT__IP=${AGENT__IP}
      - AGENT__PORT=${AGENT__PORT:-5000}
      - SCHEDULER__BASE_URL=${SCHEDULER__BASE_URL}
      - TEST_PLATFORM__BASE_URL=${TEST_PLATFORM__BASE_URL}
      - REGISTRATION__RG_ID=${REGISTRATION__RG_ID}
      - REGISTRATION__PRODUCT_ID=${REGISTRATION__PRODUCT_ID}
      - EXECUTION__MAX_PARALLEL=${EXECUTION__MAX_PARALLEL:-3}
    volumes:
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml
    restart: unless-stopped
```

- [ ] **Step 3: 提交 Docker 配置**

```bash
git add Dockerfile docker-compose.yaml
git commit -m "添加 Docker 容器化配置"
```

---

## Task 17: 最终整合与验证

**Files:**
- Verify: 所有模块导入正确

- [ ] **Step 1: 检查项目结构完整性**

```bash
# 确认所有文件已创建
ls -la app/
ls -la app/api/
ls -la app/executor/
ls -la app/git_ops/
ls -la app/clients/
ls -la app/utils/
ls -la app/models/
```

- [ ] **Step 2: 验证模块导入**

尝试运行应用，检查导入是否正常：

```bash
cd D:/code/PyTestAgent
python -c "from app.main import app; print('导入成功')"
```

- [ ] **Step 3: 最终提交（如有修改）**

```bash
git status
git add -A
git commit -m "完成 PyTestAgent 项目实现"
```

---

## 总结

本实现计划包含 17 个任务，覆盖从项目初始化到 Docker 容器化的完整流程。每个任务遵循 TDD 原则（虽然本项目主要是服务端实现，测试可后续补充），采用频繁提交策略，确保每一步都可独立验证和回溯。

**关键技术点：**

1. **配置管理** - 环境变量优先，支持 Docker 部署灵活配置
2. **日志轮转** - RotatingFileHandler 实现 100M/3 文件轮转
3. **异步执行** - FastAPI 后台任务 + asyncio 并行控制
4. **Git 操作** - subprocess 执行 Git 命令，强制还原冲突
5. **pytest 集成** - pytest-xdist 多进程并行执行
6. **定时任务** - APScheduler 实现心跳和清理任务
7. **容器化** - Dockerfile + docker-compose.yaml 完整部署方案