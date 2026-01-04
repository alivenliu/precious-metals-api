#!/bin/bash
# 安装 Playwright 浏览器依赖
playwright install --with-deps chromium
# 启动 FastAPI 应用
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
