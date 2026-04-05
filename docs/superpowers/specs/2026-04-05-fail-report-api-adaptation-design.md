# 失败上报接口适配设计

## 背景

测试平台 `/api/core/test-report/fail` 接口字段有调整，需要适配：

| 字段 | 原逻辑 | 新逻辑 |
|------|--------|--------|
| `caseName` | testcase.name | 保持不变 |
| `caseFailStep` | 空字符串 | 从 HTML 报告解析 |
| `caseFailLog` | exec_result.output/error | 从 HTML 报告解析 |
| `failReason` | 无此字段 | 新增，从 HTML 报告解析 |

## 设计方案

### 1. 依赖变更

在 `requirements.txt` 新增：
```
beautifulsoup4>=4.12.0
```

### 2. HTML 解析函数

在 `app/executor/report_handler.py` 新增 `parse_html_report()` 方法：

**输入**：HTML 报告文件路径

**输出**：
```python
{
    "caseFailStep": str,   # 失败步骤名称，多个用逗号分隔
    "caseFailLog": str,    # 失败日志
    "failReason": str      # 失败原因，多个用逗号分隔
}
```

**解析逻辑**：
- `caseFailStep`：从 `<div class="failed-steps">` 内的 `<ul class="failed-steps-list">` 中提取 `<li>` 文本
- `failReason`：从 `<div class="step-error">` 提取文本
- `caseFailLog`：从 `<div class="error-box">` 提取文本

**HTML 不存在时**：
- `caseFailStep` = ""
- `caseFailLog` = ""
- `failReason` = "HTML日志不存在"

### 3. report_failure 方法修改

修改 `ReportHandler.report_failure()` 方法：

**参数变更**：
- 新增 `repo_path: Path`
- 新增 `testcase_name: str`
- 移除 `exec_result: Dict`

**逻辑变更**：
- 调用 `parse_html_report()` 解析 HTML 报告
- 解析结果传递给 `test_platform_client.report_fail()`

### 4. test_platform_client 方法修改

修改 `TestPlatformClient.report_fail()` 方法：

**参数变更**：
- 新增 `fail_reason: str`

**data 字段**：
- 新增 `failReason` 字段

### 5. task_manager 调用方修改

修改 `TaskManager._execute_single_testcase()` 中的调用：

**参数变更**：
- 新增 `repo_path=repo_path`
- 新增 `testcase_name=testcase.name`
- 移除 `exec_result=exec_result`

## 模块影响范围

| 文件 | 改动类型 |
|------|----------|
| `requirements.txt` | 新增依赖 |
| `app/executor/report_handler.py` | 新增函数 + 修改方法 |
| `app/clients/test_platform_client.py` | 修改方法参数和 data 字段 |
| `app/executor/task_manager.py` | 修改调用参数 |

## 错误处理

- HTML 文件不存在：`failReason` = "HTML日志不存在"，其他字段为空
- HTML 解析异常：捕获异常，返回空值 + `failReason` = "HTML解析失败"