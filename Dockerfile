FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NB_HOST=0.0.0.0 \
    NB_PORT=8080

WORKDIR /app

# 安装系统依赖（如需 psycopg2 可添加 libpq-dev 等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

EXPOSE 8080

# 启动应用
CMD ["python", "app.py"]
