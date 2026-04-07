# 测试平台接口适配实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 适配测试平台新接口参数格式，确保报告上传和失败上报功能正常工作

**Architecture:** 最小化改动方案，从底层客户端向上逐层修改参数名称和添加新字段

**Tech Stack:** Python 3.x, httpx, FastAPI, asyncio

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `app/clients/test_platform_client.py` | 修改 | 核心接口客户端，参数名调整 + 新增字段 |
| `app/executor/report_handler.py` | 修改 | 调用层，参数传递调整 |
| `app/executor/task_manager.py` | 修改 | 执行层，传递新参数 |

---

### Task 1: 修改客户端 - upload_report 方法

**Files:**
- Modify: `app/clients/test_platform_client.py:118-156`

**改动说明：** 更新 upload_report 方法参数名和请求体

- [ ] **Step 1: 修改方法签名和参数构建**

将 `upload_report` 方法的参数名从 `task_id`、`case_round` 改为 `task_project_id`、`round`，并新增必填参数 `testcase_block_id`。

```python
async def upload_report(
    self,
    task_project_id: str,
    round: int,
    testcase_block_id: str,
    report_file: Path
) -> Optional[str]:
    """上传报告文件，返回报告URL"""
    if not report_file.exists():
        logger.warning(f"报告文件不存在: {report_file}")
        return None

    # 准备 FormData
    data = {
        "taskProjectID": task_project_id,
        "round": round,
        "testcaseBlockID": testcase_block_id
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
```

- [ ] **Step 2: Commit**

```bash
git add app/clients/test_platform_client.py
git commit -m "feat: 适配 upload_report 接口新参数格式"
```

---

### Task 2: 修改客户端 - report_fail 方法

**Files:**
- Modify: `app/clients/test_platform_client.py:67-116`

**改动说明：** 更新 report_fail 方法参数名、移除 totalCases、新增 testcaseBlockID

- [ ] **Step 1: 修改方法签名和参数构建**

将参数名调整，移除 `total_cases`，新增 `testcase_block_id`。

```python
async def report_fail(
    self,
    task_project_id: str,
    task_name: str,
    case_name: str,
    case_fail_step: str,
    case_fail_log: str,
    fail_reason: str,
    round: int,
    testcase_block_id: str,
    log_url: Optional[str] = None
) -> bool:
    """
    上报用例失败

    Args:
        task_project_id: 任务项目ID
        task_name: 任务名称
        case_name: 用例名称
        case_fail_step: 失败步骤
        case_fail_log: 失败日志
        fail_reason: 失败原因
        round: 轮次
        testcase_block_id: 用例块ID
        log_url: 报告URL

    Returns:
        bool: 上报是否成功
    """
    data = {
        "taskProjectID": task_project_id,
        "taskName": task_name,
        "caseName": case_name,
        "caseFailStep": case_fail_step,
        "caseFailLog": case_fail_log,
        "failReason": fail_reason,
        "round": round,
        "testcaseBlockID": testcase_block_id,
        "logUrl": log_url or "",
        "failTime": datetime.now().isoformat()
    }

    result = await self._request_with_retry("/api/core/test-report/fail", data)

    if result and "成功" in result.get("message", ""):
        logger.info("失败上报成功")
        return True

    logger.warning("失败上报失败")
    return False
```

- [ ] **Step 2: Commit**

```bash
git add app/clients/test_platform_client.py
git commit -m "feat: 适配 report_fail 接口新参数格式，移除 totalCases"
```

---

### Task 3: 修改 report_handler - process_report 方法

**Files:**
- Modify: `app/executor/report_handler.py:19-64`

**改动说明：** 更新 process_report 方法参数名，传递新参数给客户端

- [ ] **Step 1: 修改方法签名**

将参数名从 `task_id`、`case_round` 改为 `task_project_id`、`round`，新增 `testcase_block_id`。

```python
async def process_report(
    self,
    task_project_id: str,
    round: int,
    testcase_block_id: str,
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
            task_project_id=task_project_id,
            round=round,
            testcase_block_id=testcase_block_id,
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
        "caseLogUri": report_url[:255] if report_url else "",
        "tcid": testcase_uri  # 使用 testcase.uri 作为 tcid
    }

    return result_data
```

- [ ] **Step 2: Commit**

```bash
git add app/executor/report_handler.py
git commit -m "feat: 适配 process_report 方法新参数格式"
```

---

### Task 4: 修改 report_handler - report_failure 方法

**Files:**
- Modify: `app/executor/report_handler.py:66-115`

**改动说明：** 更新 report_failure 方法参数名，传递新参数给客户端

- [ ] **Step 1: 修改方法签名**

将参数名从 `task_id`、`case_round` 改为 `task_project_id`、`round`，新增 `testcase_block_id`。移除 `total_cases` 参数。

```python
async def report_failure(
    self,
    task_project_id: str,
    task_name: str,
    case_name: str,
    round: int,
    testcase_block_id: str,
    repo_path: Path,
    testcase_number: str,
    report_url: Optional[str] = None
) -> bool:
    """
    上报失败详情

    Args:
        task_project_id: 任务项目ID
        task_name: 任务名称
        case_name: 用例名称
        round: 轮次
        testcase_block_id: 用例块ID
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
        task_project_id=task_project_id,
        task_name=task_name,
        case_name=case_name,
        case_fail_step=fail_info["caseFailStep"],
        case_fail_log=fail_info["caseFailLog"],
        fail_reason=fail_info["failReason"],
        round=round,
        testcase_block_id=testcase_block_id,
        log_url=report_url
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/executor/report_handler.py
git commit -m "feat: 适配 report_failure 方法新参数格式，移除 total_cases"
```

---

### Task 5: 修改 task_manager - _execute_single_testcase 方法

**Files:**
- Modify: `app/executor/task_manager.py:158-207`

**改动说明：** 调用 report_handler 时传递新参数

- [ ] **Step 1: 更新调用参数**

将调用 `process_report` 和 `report_failure` 时的参数名调整，新增 `testcase_block_id` 传递。

```python
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
        task_project_id=context.task_project_id,
        round=int(context.run_round),
        testcase_block_id=context.testcase_block_id,
        repo_path=repo_path,
        testcase_number=testcase.number,
        testcase_uri=testcase.uri,
        exec_result=exec_result
    )

    # 失败时上报到测试平台
    if not exec_result.get('success'):
        await report_handler.report_failure(
            task_project_id=context.task_project_id,
            task_name=context.task_project_name,
            case_name=testcase.name,
            round=int(context.run_round),
            testcase_block_id=context.testcase_block_id,
            repo_path=repo_path,
            testcase_number=testcase.number,
            report_url=result_data.get('caseLogUri')
        )

    # 上报结果到调度中心
    await scheduler_client.report(
        testcase_block_id=context.testcase_block_id,
        round=context.run_round,
        results=[result_data],
        tep_id=context.group_id  # groupId 作为 tepID
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/executor/task_manager.py
git commit -m "feat: 适配 task_manager 调用新参数格式"
```

---

### Task 6: 验证改动

**改动说明：** 验证所有修改的代码语法正确，无遗漏

- [ ] **Step 1: 检查语法**

运行: `python -m py_compile app/clients/test_platform_client.py`
预期: 无输出（成功编译）

运行: `python -m py_compile app/executor/report_handler.py`
预期: 无输出（成功编译）

运行: `python -m py_compile app/executor/task_manager.py`
预期: 无输出（成功编译）

- [ ] **Step 2: 查看改动总结**

运行: `git diff --stat HEAD~5`
预期: 显示 3 个文件被修改

---

## 实施顺序

按 Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 顺序执行。

每个 Task 完成后立即 Commit，确保改动可追溯。

## 验证清单

- [ ] 所有参数名已正确替换
- [ ] testcaseBlockID 已作为必填参数传递
- [ ] totalCases 已从 report_fail 移除
- [ ] 数据流完整：task_manager → report_handler → test_platform_client
- [ ] 语法检查通过
- [ ] Git commit 完成