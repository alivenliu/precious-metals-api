FROM python:3.11-slim

# 安装 Playwright 运行所需的最小化系统依赖
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
    libpango-1-0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 关键环境变量：优化内存占用并确保日志实时显示
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# 限制 Chromium 内存占用的环境变量
ENV ELECTRON_DISABLE_GPU=1
ENV DISABLE_ESYNC=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Chromium 浏览器及其依赖
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# 暴露端口
EXPOSE 8000

# 使用 python 直接启动，确保信号处理和日志输出最直接
CMD ["python", "main.py"]
