# 失败上报接口适配实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 适配测试平台 `/api/core/test-report/fail` 接口，从 HTML 报告解析失败信息并上报。

**Architecture:** 在 report_handler 模块新增 HTML 解析函数，修改 report_failure 方法调用解析逻辑，同步修改 test_platform_client 和 task_manager 的参数传递。

**Tech Stack:** Python, BeautifulSoup4, pytest, FastAPI

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `requirements.txt` | 修改 | 新增 beautifulsoup4 依赖 |
| `app/executor/report_handler.py` | 修改 | 新增 parse_html_report 方法 + 修改 report_failure |
| `app/clients/test_platform_client.py` | 修改 | report_fail 新增 fail_reason 参数 |
| `app/executor/task_manager.py` | 修改 | 修改调用参数 |
| `tests/test_report_handler.py` | 创建 | 测试 HTML 解析逻辑 |

---

### Task 1: 新增依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 添加 beautifulsoup4 到 requirements.txt**

在 `requirements.txt` 文件末尾添加：
```
beautifulsoup4>=4.12.0
```

- [ ] **Step 2: 安装依赖**

Run: `pip install beautifulsoup4`
Expected: Successfully installed

---

### Task 2: 测试 HTML 解析功能

**Files:**
- Create: `tests/test_report_handler.py`

- [ ] **Step 1: 创建测试目录结构**

Run: `mkdir -p tests/fixtures`
Expected: 目录创建成功

- [ ] **Step 2: 创建测试 HTML fixture**

创建 `tests/fixtures/sample_fail_report.html`：

```html
<!DOCTYPE html>
<html>
<body>
<div class="failed-steps">
    <ul class="failed-steps-list">
        <li>步骤1：登录系统</li>
        <li>步骤2：提交表单</li>
    </ul>
</div>
<div class="step-error">AssertionError: 预期值与实际值不符</div>
<div class="error-box">
2024-04-05 10:00:00 ERROR: 测试执行失败
Traceback (most recent call last):
  File "test.py", line 10
    assert result == expected
AssertionError: 预期值与实际值不符
</div>
</body>
</html>
```

- [ ] **Step 3: 编写测试用例**

创建 `tests/test_report_handler.py`：

```python
import pytest
from pathlib import Path
from app.executor.report_handler import ReportHandler

def test_parse_html_report_with_valid_file():
    """测试正常 HTML 报告解析"""
    handler = ReportHandler()
    html_path = Path("tests/fixtures/sample_fail_report.html")
    
    result = handler.parse_html_report(html_path)
    
    assert result["caseFailStep"] == "步骤1：登录系统, 步骤2：提交表单"
    assert result["failReason"] == "AssertionError: 预期值与实际值不符"
    assert "测试执行失败" in result["caseFailLog"]

def test_parse_html_report_file_not_exists():
    """测试 HTML 文件不存在"""
    handler = ReportHandler()
    html_path = Path("tests/fixtures/not_exists.html")
    
    result = handler.parse_html_report(html_path)
    
    assert result["caseFailStep"] == ""
    assert result["caseFailLog"] == ""
    assert result["failReason"] == "HTML日志不存在"

def test_parse_html_report_empty_elements():
    """测试 HTML 中无失败信息"""
    handler = ReportHandler()
    html_path = Path("tests/fixtures/empty_report.html")
    
    # 创建空报告 fixture
    empty_html = "<html><body></body></html>"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(empty_html)
    
    result = handler.parse_html_report(html_path)
    
    assert result["caseFailStep"] == ""
    assert result["failReason"] == ""
    assert result["caseFailLog"] == ""
```

- [ ] **Step 4: 运行测试验证失败**

Run: `pytest tests/test_report_handler.py -v`
Expected: FAIL - parse_html_report 方法不存在

---

### Task 3: 实现 HTML 解析功能

**Files:**
- Modify: `app/executor/report_handler.py`

- [ ] **Step 1: 添加 BeautifulSoup 导入**

在 `app/executor/report_handler.py` 文件头部添加导入：

```python
from bs4 import BeautifulSoup
```

- [ ] **Step 2: 实现 parse_html_report 方法**

在 `ReportHandler` 类中添加方法：

```python
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
        soup = BeautifulSoup(open(html_path, 'r', encoding='utf-8').read(), 'html.parser')
        
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
```

- [ ] **Step 3: 运行测试验证通过**

Run: `pytest tests/test_report_handler.py -v`
Expected: PASS - 所有测试通过

- [ ] **Step 4: 提交**

```bash
git add requirements.txt app/executor/report_handler.py tests/
git commit -m "feat: 新增 HTML 报告解析功能"
```

---

### Task 4: 修改 report_failure 方法

**Files:**
- Modify: `app/executor/report_handler.py:63-87`

- [ ] **Step 1: 修改 report_failure 方法签名和实现**

替换 `report_failure` 方法（原第63-87行）：

```python
async def report_failure(
    self,
    task_id: str,
    task_name: str,
    total_cases: int,
    case_name: str,
    case_round: int,
    repo_path: Path,
    testcase_name: str,
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
        testcase_name: 测试用例名称（用于查找报告）
        report_url: 报告URL
        
    Returns:
        bool: 上报是否成功
    """
    # 查找并解析 HTML 报告
    report_file = pytest_runner.find_report_file(repo_path, testcase_name)
    
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
```

- [ ] **Step 2: 提交**

```bash
git add app/executor/report_handler.py
git commit -m "feat: 修改 report_failure 方法从 HTML 解析失败信息"
```

---

### Task 5: 修改 test_platform_client

**Files:**
- Modify: `app/clients/test_platform_client.py:61-92`

- [ ] **Step 1: 修改 report_fail 方法**

替换 `report_fail` 方法（原第61-92行）：

```python
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

    if result and result.get("code") == 200:
        logger.info("失败上报成功")
        return True

    logger.warning("失败上报失败")
    return False
```

- [ ] **Step 2: 提交**

```bash
git add app/clients/test_platform_client.py
git commit -m "feat: report_fail 新增 fail_reason 参数"
```

---

### Task 6: 修改 task_manager 调用

**Files:**
- Modify: `app/executor/task_manager.py:185-194`

- [ ] **Step 1: 修改调用参数**

找到第185-194行，修改 `report_handler.report_failure` 调用：

原代码：
```python
await report_handler.report_failure(
    task_id=context.task_id,
    task_name=context.task_project_name,
    total_cases=len(context.testcases),
    case_name=testcase.name,
    case_round=int(context.run_round),
    exec_result=exec_result,
    report_url=result_data.get('caseLogUrl')
)
```

改为：
```python
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
```

- [ ] **Step 2: 提交**

```bash
git add app/executor/task_manager.py
git commit -m "feat: 修改 task_manager 调用 report_failure 参数"
```

---

### Task 7: 验证整体功能

- [ ] **Step 1: 运行所有测试**

Run: `pytest tests/ -v`
Expected: 所有测试通过

- [ ] **Step 2: 验证模块导入**

Run: `python -c "from app.executor.report_handler import report_handler; print('OK')"`
Expected: 输出 OK

- [ ] **Step 3: 最终提交（如有遗漏）**

```bash
git status
# 如有未提交文件，补充提交
git add -A
git commit -m "chore: 完成接口适配实现"
```