import asyncio
import logging
import os
import sys
from fastapi import FastAPI, Response
from playwright.async_api import async_playwright
from datetime import datetime
from contextlib import asynccontextmanager

# 强制日志实时输出
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

async def run_scraper():
    """极其稳健的后台抓取循环"""
    logger.info("Background scraper initialized.")
    while True:
        try:
            async with async_playwright() as p:
                logger.info("Launching browser for a new scrape...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox", 
                        "--disable-setuid-sandbox", 
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                    ]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # 访问目标网站
                await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_selector("#gold", timeout=15000)
                
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
                logger.info(f"Data updated at {prices_cache['last_updated']}")
                
                await browser.close()
                # 抓取成功后等待 60 秒
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Scraper encountered an error: {e}")
            # 出错后短时间重试
            await asyncio.sleep(15)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动后台任务但不阻塞主线程
    scraper_task = asyncio.create_task(run_scraper())
    logger.info("FastAPI ready and accepting connections.")
    yield
    scraper_task.cancel()
    logger.info("FastAPI shutting down.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "online", "ready": prices_cache["ready"]}

@app.get("/prices")
async def get_prices():
    return prices_cache

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # 显式读取 Railway 的端口
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
