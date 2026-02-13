import asyncio
import logging
import os
import sys
from fastapi import FastAPI, Response
from playwright.async_api import async_playwright
from datetime import datetime
from contextlib import asynccontextmanager

# 极致日志配置：确保所有信息都能在 Railway 控制台看到
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [SCRAPER] %(levelname)s: %(message)s',
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
    """V7 极速自修复抓取逻辑"""
    logger.info("Scraper service started. Preparing to launch browser...")
    
    # 给系统一点启动缓冲时间
    await asyncio.sleep(5)
    
    while True:
        playwright = None
        browser = None
        try:
            playwright = await async_playwright().start()
            logger.info("Playwright initialized. Launching Chromium with optimized args...")
            
            # 针对 Railway 资源限制优化的启动参数
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--no-zygote"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # 设置全局超时
            context.set_default_timeout(30000)
            
            while True:
                try:
                    page = await context.new_page()
                    logger.info("Connecting to profinance.ru...")
                    
                    # 尝试访问，如果 networkidle 太慢，降级为 domcontentloaded
                    try:
                        await page.goto("https://www.profinance.ru/quotes/", wait_until="networkidle", timeout=45000)
                    except Exception as e:
                        logger.warning(f"Networkidle timeout, falling back to domcontentloaded: {e}")
                        await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=20000)
                    
                    # 等待数据加载
                    await page.wait_for_selector("#gold", timeout=15000)
                    
                    # 额外等待以确保实时脚本运行
                    await asyncio.sleep(3)
                    
                    ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
                    results = {}
                    for item_id in ids:
                        try:
                            bid = await page.locator(f"#{item_id} .quote__row__cell--bid").inner_text()
                            ask = await page.locator(f"#{item_id} .quote__row__cell--ask").inner_text()
                            results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                        except:
                            results[item_id] = {"bid": "N/A", "ask": "N/A"}
                    
                    # 成功获取数据，更新全局缓存
                    prices_cache["data"] = results
                    prices_cache["status"] = "success"
                    prices_cache["last_updated"] = datetime.now().isoformat()
                    prices_cache["ready"] = True
                    prices_cache["error_log"] = None
                    logger.info(f"Successfully fetched prices: Gold={results.get('gold', {}).get('bid')}")
                    
                    await page.close()
                    # 每 45 秒更新一次
                    await asyncio.sleep(45)
                    
                except Exception as e:
                    logger.error(f"Iteration failed: {e}")
                    prices_cache["status"] = "iteration_error"
                    prices_cache["error_log"] = str(e)
                    await asyncio.sleep(10)
                    break # 跳出内循环，重置浏览器
                    
        except Exception as e:
            logger.error(f"Critical scraper error: {e}")
            prices_cache["status"] = "critical_error"
            prices_cache["error_log"] = str(e)
            await asyncio.sleep(20)
        finally:
            if browser:
                try: await browser.close()
                except: pass
            if playwright:
                try: await playwright.stop()
                except: pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI Application Starting...")
    scraper_task = asyncio.create_task(run_scraper())
    yield
    logger.info("FastAPI Application Shutting Down...")
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
    # 强制单工作进程以节省内存
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
