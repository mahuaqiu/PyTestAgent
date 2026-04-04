# PyTestAgent 设计文档

## 项目概述

PyTestAgent 是一个基于 FastAPI + Docker 的测试执行代理服务，用于接受调度中心平台的调度，执行 Python pytest 测试用例，并上报执行结果。

## 核心流程

### 主流程

1. **启动注册** - PyTestAgent 启动时向调度中心发起注册，机器状态标记为在线
2. **任务接收** - 调度中心调用 sendJob 接口，PyTestAgent 立即返回成功，后台异步执行，机器状态标记为使用中
3. **结果上报** - 用例产生结果时，调用调度中心 report 接口上报
4. **任务完成** - 所有用例执行完成后，调用调度中心 complete 接口
5. **任务关闭** - 调度中心收到 complete 后调用 closeJob 接口，机器状态标记为在线

### 分支流程（停止任务）

1. 用户在调度中心点击停止
2. 调度中心调用 stopJob 接口
3. PyTestAgent 立即返回成功
4. 当前用例执行完成后停止，不再下发新任务
5. 上报 report → 等待 10 秒 → 上报 complete

### 心跳机制

- 每 2 分钟向调度中心上报心跳
- 未上报则调度中心将机器状态标记为离线

## 项目结构

```
PyTestAgent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理（环境变量优先）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API 路由定义
│   │   ├── schemas.py          # 请求/响应模型
│   │   └── handlers.py         # 请求处理器
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── task_manager.py     # 任务执行管理（串行/并行调度）
│   │   ├── pytest_runner.py    # pytest 执行器
│   │   └── report_handler.py   # 报告处理和上传
│   ├── git_ops/
│   │   ├── __init__.py
│   │   └── repo_manager.py     # Git 仓库操作
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── scheduler_client.py # 调度中心接口客户端
│   │   └── test_platform_client.py # 测试平台接口客户端
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py           # 日志配置（100M/3文件轮转）
│   │   └── scheduler.py        # 定时任务（心跳、report清理）
│   └── models/
│       ├── __init__.py
│       └── task_context.py     # 任务执行上下文模型
├── config.yaml                 # 默认配置文件
├── requirements.txt            # Python 依赖
├── Dockerfile                  # Docker 构建文件
├── docker-compose.yaml         # Docker Compose 配置
├── .env.example                # 环境变量示例
└── logs/                       # 日志目录（运行时生成）
```

## 配置管理

### config.yaml 默认配置

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

### 环境变量覆盖规则

- 使用 `__` 分隔嵌套层级
- 例如：`AGENT__IP` 覆盖 `agent.ip`
- 环境变量存在时优先使用，不存在则使用 config.yaml 的值

### IP 配置

- 支持大网/小网 IP 配置
- 用于注册时的 `groupId`、`name`、`url` 字段构建

## API 接口设计

### 对外接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/sendJob` | POST | 接收任务，立即返回成功，后台异步执行 |
| `/stopJob` | POST | 停止任务，立即返回成功，完成当前用例后停止 |
| `/closeJob` | POST | 关闭任务，立即返回成功 |

### 请求/响应格式

- 请求 header 包含 `request_id`（随机字符串）
- 响应 header 回传相同的 `request_id`
- 响应格式：`{"param": {"status": "ok", "result": ""}, "header": {...}}`

### 处理逻辑

| 接口 | 处理流程 |
|------|----------|
| `sendJob` | 1. 解析参数并记录日志<br>2. 立即返回成功响应<br>3. 启动后台任务执行 |
| `stopJob` | 1. 设置停止标志到当前任务上下文<br>2. 立即返回成功响应<br>3. 任务执行器检测到标志后停止下发新用例 |
| `closeJob` | 1. 清理当前任务上下文<br>2. 立即返回成功响应 |

## 任务执行流程

### 执行流程图

```
收到 sendJob 后：

1. 解析 userExtendContent 获取 git_url 和 exeParam
2. 调用 repo_manager 准备仓库（clone/pull/切换分支）
3. 根据 taskType 决定执行模式：
   - taskType=5（并行）→ 并行执行，最多 max_parallel 条
   - 其他 → 串行执行，一条完成后再执行下一条
4. 对每个 testcase：
   ├─ 调用 pytest_runner 执行
   ├─ 执行失败 → 调用 test_platform_client.fail()
   ├─ 调用 test_platform_client.upload() 获取报告地址
   ├─ 调用 scheduler_client.report() 上报结果
   ├─ 检测 stopJob 标志 → 若已停止，跳过后续用例
5. 所有用例完成后：
   ├─ 等待 10 秒
   ├─ 调用 scheduler_client.complete()（失败重试一次）
```

### pytest 执行逻辑

| 步骤 | 说明 |
|------|------|
| 路径拼接 | 将 `{work_dir}/{git_repo_name}/{svnScriptPath}` 拼接为完整路径 |
| 构建命令 | `pytest {full_path} --exeParam={json}` |
| 并行模式 | 使用 `pytest-xdist -n {max_parallel}` 多进程执行 |
| 串行模式 | 逐条执行，每条完成后立即上报 |
| 报告匹配 | 执行后从 `{work_dir}/{git_repo_name}/report/` 目录匹配 `{testcase_name}.html` |

### 路径示例

```
svnScriptPath: "testcase/web/test_auto_test.py"
git_url: "https://github.com/example/test-repo.git"

完整执行路径: /home/test-repo/testcase/web/test_auto_test.py
报告路径: /home/test-repo/report/test_auto_test.html
```

## Git 仓库管理

### 仓库准备流程

```
1. 从 git_url 解析仓库名（如 test-repo.git → test-repo）
2. 检查 {work_dir}/{repo_name} 是否存在：
   ├─ 不存在 → git clone {git_url}
   ├─ 存在 → 进入仓库目录
3. 获取 exeParam 中的 branch 参数（默认 master）
4. 检查当前分支是否匹配：
   ├─ 不匹配 → git checkout {branch}
   │   ├─ 有本地修改冲突 → git checkout -- . 强制还原
   │   └─ 然后切换分支
   ├─ 匹配 → 继续
5. git pull 更新到最新
```

### Git 认证

- HTTPS + Token 方式
- Token 直接包含在 git_url 中

## 外部服务客户端

### 调度中心接口

| 接口 | 调用时机 | 参数 |
|------|----------|------|
| `register` | 启动时调用一次 | agent 配置信息列表 |
| `heartbeat` | 每 2 分钟调用 | 注册返回的 ID 列表 |
| `report` | 每条用例执行完成后 | 用例结果、时间、报告地址等 |
| `complete` | 所有用例完成后（等待10秒） | taskID、schedulerBlockID 等 |

### 测试平台接口

| 接口 | 调用时机 | 参数 |
|------|----------|------|
| `fail` | 用例执行失败时 | taskId、caseName、失败日志等 |
| `upload` | 每条用例执行完成后（无论成功失败） | task_id、case_round、报告 HTML 文件 |

### 重试策略

- 所有接口失败时最多重试 1 次
- 重试间隔：等待 2 秒后重试
- 最终失败记录日志

## 状态管理

- 状态由调度中心统一管理
- PyTestAgent 本地仅维护当前任务执行上下文
- 单进程单容器架构

## 日志和定时任务

### 日志配置

| 配置项 | 值 |
|--------|-----|
| 日志格式 | `{timestamp} - {level} - {message}` |
| 文件路径 | `logs/pytest_agent.log` |
| 最大文件大小 | 100MB |
| 备份文件数量 | 3 个 |
| 记录内容 | 请求参数、返回结果、异常详细报错行数 |

### 定时任务

| 任务 | 间隔 | 功能 |
|------|------|------|
| 心跳上报 | 每 2 分钟 | 调用 scheduler_client.heartbeat() |
| report 清理 | 每 24 小时 | 清理各仓库 `/report` 目录下 7 天前的 HTML 文件 |

## Docker 容器化部署

### Dockerfile

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

### requirements.txt

```
fastapi>=0.100.0
uvicorn>=0.23.0
pytest>=7.0.0
pytest-xdist>=3.0.0
pytest-html>=3.0.0
pyyaml>=6.0
httpx>=0.24.0
apscheduler>=3.10.0
```

### docker-compose.yaml

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

### .env.example

```bash
AGENT__IP=192.168.0.100
AGENT__PORT=5000
SCHEDULER__BASE_URL=http://scheduler-center:8080
TEST_PLATFORM__BASE_URL=http://test-platform:8000
REGISTRATION__RG_ID=your_rg_id
REGISTRATION__PRODUCT_ID=your_product_id
EXECUTION__MAX_PARALLEL=3
```

## 设计决策记录

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 配置优先级 | 环境变量优先 | 符合 Docker 最佳实践 |
| 调度中心地址 | 单一 base_url | 简单清晰，易于配置 |
| 测试平台地址 | 独立配置 | 与调度中心分离，灵活部署 |
| 并行限制 | 可配置，默认 3 | 灵活适应不同机器性能 |
| 工作目录 | 固定 /home/ | 容器内固定路径，仓库保留 |
| 状态管理 | 依赖调度中心 | 单进程架构，状态集中管理 |
| Git 认证 | HTTPS + Token（URL内置） | 简单可靠 |
| 重试策略 | 最多重试 1 次 | 平衡可靠性和响应速度 |
| 基础镜像 | python:3.11.13-slim-bookworm | 用户本地已有镜像 |