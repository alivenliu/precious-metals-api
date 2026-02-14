import asyncio
import logging
import os
import sys
from fastapi import FastAPI
from playwright.async_api import async_playwright
from datetime import datetime
from contextlib import asynccontextmanager

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [V13-SMART] %(levelname)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("profinance-api")

# 全局数据缓存
prices_cache = {
    "data": {},
    "status": "initializing",
    "last_updated": None,
    "ready": False,
    "error_log": None,
    "next_refresh_interval": 300 # 默认 5 分钟
}

def get_refresh_interval():
    """
    根据当前时间决定刷新间隔：
    工作日 (周一至周五): 5 分钟 (300秒)
    周末 (周六至周日): 1 小时 (3600秒)
    """
    now = datetime.now()
    weekday = now.weekday() # 0 是周一, 6 是周日
    
    if weekday < 5: # 周一至周五
        interval = 300
        mode = "Weekday (5m)"
    else: # 周六和周日
        interval = 3600
        mode = "Weekend (1h)"
        
    return interval, mode

async def run_scraper():
    """V13 智能调度版：支持动态刷新频率"""
    logger.info("V13 Smart Scraper starting...")
    await asyncio.sleep(5)
    
    while True:
        try:
            async with async_playwright() as p:
                logger.info("Launching browser engine...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # 拦截无关资源提速
                await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
                
                try:
                    logger.info("Accessing profinance.ru/quotes/ ...")
                    await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=60000)
                    
                    # 等待报价行加载
                    await page.wait_for_selector(".quote__row", timeout=30000)
                    
                    # 额外缓冲确保 JS 数据填充完成
                    await asyncio.sleep(5)
                    
                    # 目标资产名称映射
                    targets = {
                        "gold": "Gold",
                        "silver": "Silver",
                        "platinum": "Platinum",
                        "palladium": "Palladium",
                        "USDCNY": "USD/CNY",
                        "USDCNH": "USD/CNH",
                        "USDHKD": "USD/HKD"
                    }
                    
                    results = {}
                    rows = await page.locator(".quote__row").all()
                    
                    for row in rows:
                        name_el = row.locator(".quote__row__cell--name")
                        if await name_el.count() > 0:
                            name = await name_el.inner_text()
                            name = name.strip()
                            
                            for key, target_name in targets.items():
                                if name == target_name:
                                    bid_el = row.locator(".quote__row__cell--bid")
                                    ask_el = row.locator(".quote__row__cell--ask")
                                    
                                    bid = await bid_el.inner_text() if await bid_el.count() > 0 else "N/A"
                                    ask = await ask_el.inner_text() if await ask_el.count() > 0 else "N/A"
                                    
                                    results[key] = {
                                        "bid": bid.strip(),
                                        "offer": ask.strip()
                                    }
                    
                    if results:
                        prices_cache["data"] = results
                        prices_cache["status"] = "success"
                        prices_cache["last_updated"] = datetime.now().isoformat()
                        prices_cache["ready"] = True
                        prices_cache["error_log"] = None
                        logger.info(f"Update successful. {len(results)} items captured.")
                    else:
                        raise Exception("Failed to find target assets.")
                        
                except Exception as e:
                    logger.error(f"Scrape error: {e}")
                    prices_cache["status"] = "error"
                    prices_cache["error_log"] = str(e)
                
                await browser.close()
                
                # 计算下一次刷新间隔
                interval, mode = get_refresh_interval()
                prices_cache["next_refresh_interval"] = interval
                logger.info(f"Next refresh in {interval}s (Mode: {mode})")
                await asyncio.sleep(interval)
                
        except Exception as e:
            logger.error(f"Engine error: {e}")
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_scraper())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    interval, mode = get_refresh_interval()
    return {
        "version": "V13-SMART",
        "ready": prices_cache["ready"],
        "current_mode": mode,
        "next_refresh_seconds": interval,
        "last_updated": prices_cache["last_updated"]
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
