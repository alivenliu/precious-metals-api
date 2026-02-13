import asyncio
import logging
import os
import sys
from fastapi import FastAPI
from playwright.async_api import async_playwright
from datetime import datetime
from contextlib import asynccontextmanager

# 极致日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [V8-STABLE] %(levelname)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("profinance-api")

# 全局数据缓存
prices_cache = {
    "data": {},
    "status": "initializing",
    "last_updated": None,
    "ready": False,
    "error_log": None
}

async def run_scraper():
    """V8 强力突破版：资源拦截 + 极速加载"""
    logger.info("V8 Scraper service starting...")
    await asyncio.sleep(2) # 启动缓冲
    
    while True:
        try:
            async with async_playwright() as p:
                logger.info("Launching optimized browser...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox", 
                        "--disable-setuid-sandbox", 
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process"
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
                
                # 核心优化：拦截无关资源以节省流量和时间
                page = await context.new_page()
                await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())
                
                logger.info("Navigating to target with 40s timeout...")
                try:
                    # 采用 commit 级别加载，只要收到数据就开始尝试解析
                    await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=40000)
                    
                    # 关键：只要目标元素出现就停止等待
                    await page.wait_for_selector("#gold", timeout=20000)
                    
                    # 稍微等待数据渲染
                    await asyncio.sleep(2)
                    
                    ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
                    results = {}
                    for item_id in ids:
                        try:
                            bid = await page.locator(f"#{item_id} .quote__row__cell--bid").inner_text()
                            ask = await page.locator(f"#{item_id} .quote__row__cell--ask").inner_text()
                            results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                        except:
                            results[item_id] = {"bid": "N/A", "ask": "N/A"}
                    
                    # 更新成功
                    prices_cache["data"] = results
                    prices_cache["status"] = "success"
                    prices_cache["last_updated"] = datetime.now().isoformat()
                    prices_cache["ready"] = True
                    prices_cache["error_log"] = None
                    logger.info(f"Update successful: {results.get('gold')}")
                    
                except Exception as e:
                    logger.error(f"Page load/parse error: {e}")
                    prices_cache["status"] = "load_error"
                    prices_cache["error_log"] = str(e)
                
                await browser.close()
                # 成功或失败都等待 60 秒再进行下一次尝试
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Playwright engine error: {e}")
            await asyncio.sleep(20)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scraper_task = asyncio.create_task(run_scraper())
    yield
    scraper_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "status": "online", 
        "scraper_status": prices_cache["status"],
        "ready": prices_cache["ready"],
        "last_updated": prices_cache["last_updated"],
        "error": prices_cache["error_log"]
    }

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
