# 使用 Playwright 官方提供的 Python 镜像，该镜像已内置所有浏览器依赖
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# 告诉 Playwright 浏览器已经安装在镜像中了
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 注意：官方镜像已经预装了浏览器，但为了保险我们运行一次轻量级检查
# 如果已经存在则会秒过
RUN playwright install chromium

# 复制源代码
COPY . .

EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
