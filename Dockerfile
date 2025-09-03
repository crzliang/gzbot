########################################
# Builder: 构建第三方依赖为 wheels
########################################
FROM python:3.12 AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt ./
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && python -m pip install -U pip \
 && pip wheel -w /wheels --prefer-binary --only-binary=:all: -r requirements.txt \
 && apt-get purge -y --auto-remove build-essential \
 && rm -rf /var/lib/apt/lists/*

########################################
# Final: 仅安装 wheels + 复制应用代码
########################################
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NB_HOST=0.0.0.0 \
    NB_PORT=8080

WORKDIR /app

# 安装依赖（离线，避免拉取多余构建链）
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install -U pip \
 && pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels /root/.cache \
 && find /usr/local -type d -name '__pycache__' -prune -exec rm -rf {} +

# 复制代码
COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
