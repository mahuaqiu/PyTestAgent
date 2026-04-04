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