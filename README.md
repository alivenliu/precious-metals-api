# 贵金属实时价格 API 部署指南

本项目是一个基于 FastAPI 和 Playwright 的实时价格抓取 API，从 `profinance.ru` 获取金、银、铂、钯的实时报价。

## 部署步骤 (以 Railway 为例)

1. **创建 GitHub 仓库**：
   - 在 GitHub 上创建一个新的私有或公开仓库。
   - 将本项目的所有文件（`main.py`, `requirements.txt`, `start.sh`, `Dockerfile`, `README.md`）上传到该仓库。

2. **连接 Railway**：
   - 登录 [Railway.app](https://railway.app/)。
   - 点击 **"New Project"** -> **"Deploy from GitHub repo"**。
   - 选择您刚才创建的仓库。

3. **配置变量 (可选)**：
   - Railway 会自动识别 `Dockerfile` 或 `start.sh`。
   - 如果需要自定义端口，可以在 Railway 的 **Variables** 选项卡中添加 `PORT` 变量（默认为 8000）。

4. **完成部署**：
   - 部署完成后，Railway 会为您提供一个公网 URL（如 `https://your-project.up.railway.app`）。
   - 访问 `https://your-project.up.railway.app/prices` 即可获取实时数据。

## 本地运行测试

如果您想在本地运行：

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 启动服务
python main.py
```

## 接口说明

- **URL**: `/prices`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "gold": { "bid": 4331.04, "offer": 4331.92 },
    "silver": { "bid": 72.55, "offer": 72.59 },
    "platinum": { "bid": 2136.6, "offer": 2145.96 },
    "palladium": { "bid": 1636.09, "offer": 1645.6 }
  }
  ```
