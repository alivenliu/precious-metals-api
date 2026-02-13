FROM python:3.11-slim

WORKDIR /app

# 只需要基础的 Python 环境
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 极速启动
CMD ["python", "main.py"]
