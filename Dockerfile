FROM python:3.11-slim

# 安装 Playwright 所需的系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 环境变量优化
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# 限制 Playwright 的并发和内存
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# 使用 uvicorn 启动，并设置合理的超时和工作进程
# --workers 1 确保不会因为多进程导致内存溢出
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "60"]
