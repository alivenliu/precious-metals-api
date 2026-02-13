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
    """优化后的稳健抓取循环，确保数据实时性"""
    logger.info("Real-time scraper initialized.")
    while True:
        try:
            async with async_playwright() as p:
                logger.info("Launching browser for real-time update...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox", 
                        "--disable-setuid-sandbox", 
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                    ]
                )
                # 禁用缓存以确保获取最新页面
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    ignore_https_errors=True
                )
                page = await context.new_page()
                
                # 访问目标网站，使用 networkidle 确保所有实时脚本已加载
                logger.info("Navigating to profinance.ru...")
                await page.goto("https://www.profinance.ru/quotes/", wait_until="networkidle", timeout=60000)
                
                # 关键：等待一小段时间（如 5 秒），让页面的实时更新逻辑（WebSocket/SSE）同步最新报价
                logger.info("Waiting for data synchronization...")
                await asyncio.sleep(5)
                
                await page.wait_for_selector("#gold", timeout=20000)
                
                ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
                results = {}
                for item_id in ids:
                    try:
                        # 重新获取最新文本
                        bid_el = page.locator(f"#{item_id} .quote__row__cell--bid")
                        ask_el = page.locator(f"#{item_id} .quote__row__cell--ask")
                        
                        bid = await bid_el.inner_text()
                        ask = await ask_el.inner_text()
                        
                        results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                    except Exception as e:
                        logger.warning(f"Could not find data for {item_id}: {e}")
                        results[item_id] = {"bid": "N/A", "ask": "N/A"}
                
                # 更新缓存
                prices_cache["data"] = results
                prices_cache["status"] = "success"
                prices_cache["last_updated"] = datetime.now().isoformat()
                prices_cache["ready"] = True
                logger.info(f"Real-time data updated: {results.get('gold')}")
                
                await browser.close()
                # 缩短抓取间隔，提高频率（可选，此处设为 30 秒以平衡负载和实时性）
                await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scraper_task = asyncio.create_task(run_scraper())
    logger.info("API lifespan started.")
    yield
    scraper_task.cancel()
    logger.info("API lifespan ended.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "online", "ready": prices_cache["ready"], "last_updated": prices_cache["last_updated"]}

@app.get("/prices")
async def get_prices():
    return prices_cache

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
