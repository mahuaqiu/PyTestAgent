# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

PyTestAgent 是一个基于 FastAPI + Docker 的测试执行代理服务，接受调度中心的调度，执行 pytest 测试用例并上报结果。

## 常用命令

```bash
# 本地运行（需先激活虚拟环境）
python -m app.main

# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 5000

# Docker 部署
docker-compose up -d

# 安装依赖（在虚拟环境中）
pip install -r requirements.txt
```

## 配置管理

- 配置文件：`config.yaml` 提供默认值
- 环境变量优先：使用 `__` 分隔嵌套层级，如 `AGENT__IP` 覆盖 `agent.ip`
- 关键配置项：
  - `AGENT__IP/PORT`：代理服务地址
  - `SCHEDULER__BASE_URL`：调度中心地址
  - `TEST_PLATFORM__BASE_URL`：测试平台地址
  - `EXECUTION__MAX_PARALLEL`：最大并行数（默认 3）
  - `EXECUTION__TESTCASE_TIMEOUT`：用例超时时间（秒，默认 3600）

## 核心架构

```
app/
├── main.py           # FastAPI 入口，生命周期管理（启动注册、心跳、定时任务）
├── config.py         # 配置管理，环境变量优先
├── api/              # API 层：routes → handlers → schemas
├── executor/         # 执行层
│   ├── task_manager.py    # 任务执行管理（串行/并行调度、停止控制）
│   ├── pytest_runner.py   # pytest 执行器（命令构建、超时控制）
│   └── report_handler.py  # 报告处理和上传
├── clients/          # 外部服务客户端
│   ├── scheduler_client.py    # 调度中心：register/heartbeat/report/complete
│   └── test_platform_client.py # 测试平台：fail/upload
├── git_ops/          # Git 操作：clone/pull/分支切换（强制还原冲突）
├── utils/            # 工具：logger（100M/3文件轮转）、scheduler（心跳/清理）
└── models/           # 数据模型：TaskContext（线程安全、停止标志）
```

## 核心流程

1. **启动** → 向调度中心注册 → 启动定时任务（心跳每2分钟、报告清理每24小时）
2. **sendJob** → 立即返回成功 → 后台异步执行任务
3. **执行** → 准备仓库（clone/pull/切换分支）→ 串行/并行执行 pytest → 上报结果
4. **stopJob** → 设置停止标志 → 当前用例完成后停止
5. **complete** → 等待10秒 → 上报完成（失败重试1次）

## 执行模式

- `executeType=1`：串行执行，逐条完成并上报
- `executeType=2`：并行执行，使用 asyncio.Semaphore 控制最大并发数（由 `max_parallel` 配置）
  - 每个用例在独立 pytest 进程中执行，互不影响
  - 单条用例完成后立即上报结果

## 设计要点

- **全局实例**：各模块使用单例模式（`config`、`task_manager`、`scheduler_client` 等）
- **线程安全**：TaskContext 使用 `threading.Lock` 保护停止标志
- **重试策略**：外部接口失败最多重试1次，间隔2秒
- **报告路径**：`{repo_path}/report/{testcase_name}.html`
- **Git 强制还原**：分支切换冲突时 `git checkout -- .` 强制还原