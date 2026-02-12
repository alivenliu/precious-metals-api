import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from playwright.async_api import async_playwright
from datetime import datetime

# 配置日志输出到标准输出，方便 Railway 抓取
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("profinance-api")

# 全局数据缓存
prices_cache = {
    "data": {},
    "status": "initializing",
    "last_updated": None,
    "ready": False
}

async def fetch_data():
    """独立的抓取逻辑，带有严格的超时和资源限制"""
    logger.info("Starting a new scrape attempt...")
    try:
        async with async_playwright() as p:
            # 限制资源占用的启动参数
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process" # 减少进程开销
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # 设置较短的页面加载超时
            await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector("#gold", timeout=10000)
            
            ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
            results = {}
            for item_id in ids:
                try:
                    bid = await page.locator(f"#{item_id} .quote__row__cell--bid").inner_text()
                    ask = await page.locator(f"#{item_id} .quote__row__cell--ask").inner_text()
                    results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                except:
                    results[item_id] = {"bid": "N/A", "ask": "N/A"}
            
            # 更新缓存
            prices_cache["data"] = results
            prices_cache["status"] = "success"
            prices_cache["last_updated"] = datetime.now().isoformat()
            prices_cache["ready"] = True
            logger.info("Scrape successful.")
            
            await browser.close()
    except Exception as e:
        logger.error(f"Scrape failed: {str(e)}")
        prices_cache["status"] = f"error: {str(e)}"

async def scraper_task():
    """循环抓取任务"""
    while True:
        await fetch_data()
        # 每 60 秒抓取一次
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 关键：不要在这里 await 抓取任务，使用 create_task 让它在后台运行
    # 这样 FastAPI 就能立即启动并响应端口
    logger.info("API lifespan starting...")
    bg_task = asyncio.create_task(scraper_task())
    yield
    logger.info("API lifespan ending...")
    bg_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    # 始终返回 200，确保 Railway 健康检查通过
    return {"status": "online", "ready": prices_cache["ready"]}

@app.get("/prices")
async def get_prices():
    return prices_cache

@app.get("/health")
async def health():
    return {"status": "ok"}
