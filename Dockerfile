# 使用包含 Playwright 依赖的官方镜像
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["sh", "start.sh"]
