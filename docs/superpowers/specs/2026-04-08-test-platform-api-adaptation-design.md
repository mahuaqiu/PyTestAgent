# 测试平台接口适配设计

**日期：** 2026-04-08  
**作者：** Claude Code  
**状态：** 待审查

## 背景

测试平台接口更新，需要适配新的参数格式：

1. **报告上传接口** `/api/core/test-report/upload` - 参数名变化 + 新增必填字段
2. **失败用例上报接口** `/api/core/test-report/fail` - 参数名变化 + 移除字段
3. **sendjob API** - 字段结构确认

## 接口变化详情

### 1. 报告上传接口 `/api/core/test-report/upload`

**请求方式：** POST (multipart/form-data)

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|-----|------|
| taskProjectID | string | ✅ | 任务项目ID |
| round | int | ✅ | 执行轮次 |
| testcaseBlockID | string | ✅ | 用例块ID |
| file | file | ✅ | HTML 文件 |

**变化对比：**
- `task_id` → `taskProjectID`
- `case_round` → `round`
- 新增 `testcaseBlockID`（必填）

### 2. 失败用例上报接口 `/api/core/test-report/fail`

**请求方式：** POST (JSON)

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|-----|------|
| taskProjectID | string | ✅ | 任务项目ID |
| taskName | string | ✅ | 任务名称 |
| caseName | string | ✅ | 用例标题 |
| caseFailStep | string | ✅ | 失败步骤名称 |
| caseFailLog | string | ✅ | 失败日志内容 |
| failReason | string | ❌ | 失败原因（可选） |
| round | int | ✅ | 执行轮次 |
| testcaseBlockID | string | ❌ | 用例块ID（可选） |
| logUrl | string | ❌ | 日志HTML文件路径（可选） |
| failTime | datetime | ❌ | 失败时间（可选，ISO格式） |

**变化对比：**
- `taskId` → `taskProjectID`
- 移除 `totalCases`
- `caseRound` → `round`
- 新增 `testcaseBlockID`（可选）

### 3. sendjob API 字段来源

从 sendjob API 参数中获取：

- `param.testcaseBlockID`: 任务级别的组合用例块 ID（用于上传报告）
- `param.taskProjectID`: 任务项目 ID
- `param.runRound`: 执行轮次
- `testcase[].testcaseBlockId`: 单个用例的块 ID（可选）

## 设计方案

采用**最小化改动**方案，只修改必要的参数名称和添加新字段。

### 文件改动清单

| 文件 | 改动内容 |
|------|---------|
| `app/clients/test_platform_client.py` | 参数名调整 + 新增 testcaseBlockID |
| `app/executor/report_handler.py` | 调用参数调整 |
| `app/executor/task_manager.py` | 传递 testcaseBlockID |

### 代码改动详情

#### 1. `app/clients/test_platform_client.py`

**upload_report 方法改动：**

```python
async def upload_report(
    self,
    task_project_id: str,       # task_id → task_project_id
    round: int,                  # case_round → round
    testcase_block_id: str,     # 新增必填参数
    report_file: Path
) -> Optional[str]:
```

请求参数构建：
```python
data = {
    "taskProjectID": task_project_id,
    "round": round,
    "testcaseBlockID": testcase_block_id
}
```

**report_fail 方法改动：**

```python
async def report_fail(
    self,
    task_project_id: str,       # taskId → task_project_id
    task_name: str,
    case_name: str,
    case_fail_step: str,
    case_fail_log: str,
    fail_reason: str,
    round: int,                  # case_round → round
    testcase_block_id: str,     # 新增参数
    log_url: Optional[str] = None
) -> bool:
```

请求参数构建（移除 totalCases）：
```python
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
```

#### 2. `app/executor/report_handler.py`

**process_report 方法改动：**

```python
async def process_report(
    self,
    task_project_id: str,       # task_id → task_project_id
    round: int,                  # case_round → round
    testcase_block_id: str,     # 新增参数
    repo_path: Path,
    testcase_number: str,
    testcase_uri: str,
    exec_result: Dict
) -> Dict:
```

调用上传接口时传递新参数：
```python
report_url = await test_platform_client.upload_report(
    task_project_id=task_project_id,
    round=round,
    testcase_block_id=testcase_block_id,
    report_file=report_file
)
```

**report_failure 方法改动：**

```python
async def report_failure(
    self,
    task_project_id: str,       # task_id → task_project_id
    task_name: str,
    case_name: str,
    round: int,                  # case_round → round
    testcase_block_id: str,     # 新增参数
    repo_path: Path,
    testcase_number: str,
    report_url: Optional[str] = None
) -> bool:
```

调用失败上报接口时传递新参数：
```python
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

#### 3. `app/executor/task_manager.py`

**_execute_single_testcase 方法改动：**

调用 report_handler 时传递新参数：

```python
# 处理报告和上报
result_data = await report_handler.process_report(
    task_project_id=context.task_project_id,  # 使用 task_project_id
    round=int(context.run_round),
    testcase_block_id=context.testcase_block_id,  # 新增参数
    repo_path=repo_path,
    testcase_number=testcase.number,
    testcase_uri=testcase.uri,
    exec_result=exec_result
)

# 失败时上报
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
```

### 数据流图

```
sendjob API
    ↓
param.testcaseBlockID → context.testcase_block_id
param.taskProjectID → context.task_project_id
param.runRound → context.run_round
    ↓
task_manager._execute_single_testcase
    ↓ (传递 testcase_block_id)
report_handler.process_report / report_failure
    ↓ (传递 testcase_block_id)
test_platform_client.upload_report / report_fail
    ↓
测试平台接口
```

## 验证方法

1. 发送测试任务，检查日志中的请求参数是否正确
2. 检查测试平台是否正确接收报告和失败信息
3. 验证上传的报告 URL 是否可访问

## 风险评估

- **风险：** 低。仅参数名调整，逻辑不变。
- **回滚：** 如有问题，可快速回退到旧参数格式。

## 实施顺序

1. 修改 `test_platform_client.py`（核心接口客户端）
2. 修改 `report_handler.py`（调用层）
3. 修改 `task_manager.py`（传递层）
4. 测试验证