import asyncio
import logging
import os
import sys
from fastapi import FastAPI
from playwright.async_api import async_playwright
from datetime import datetime
from contextlib import asynccontextmanager

# 极致日志配置：使用 V10-B 标识符以区分旧版
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [V10-B-ULTRA] %(levelname)s: %(message)s',
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
    """V10-B 纯净修复版：强力定位 + 强制日志更新"""
    logger.info("V10-B Scraper initializing... Waiting for network stability.")
    await asyncio.sleep(10)
    
    while True:
        try:
            async with async_playwright() as p:
                logger.info("Launching Chromium engine...")
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
                    logger.info("Navigating to https://www.profinance.ru/quotes/ ...")
                    # 使用 domcontentloaded 快速进入
                    await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=60000)
                    
                    # 强力等待关键元素
                    logger.info("Waiting for dynamic content to render (V10-B)...")
                    await page.wait_for_selector(".quote__row__cell--bid", timeout=30000)
                    
                    # 额外缓冲确保所有数据同步
                    await asyncio.sleep(5)
                    
                    # 目标资产 ID 映射
                    targets = {
                        "gold": "Gold",
                        "silver": "Silver",
                        "platinum": "Platinum",
                        "palladium": "Palladium",
                        "USDCNY": "USD/CNY",
                        "USDCNH": "USD/CNH"
                    }
                    
                    results = {}
                    # 遍历页面所有行，寻找匹配的名称
                    rows = await page.locator(".quote__row").all()
                    logger.info(f"Scanning {len(rows)} table rows...")
                    
                    for row in rows:
                        name_el = row.locator(".quote__row__cell--name")
                        if await name_el.count() > 0:
                            name = await name_el.inner_text()
                            name = name.strip()
                            
                            for key, target_name in targets.items():
                                if name == target_name:
                                    bid = await row.locator(".quote__row__cell--bid").inner_text()
                                    ask = await row.locator(".quote__row__cell--ask").inner_text()
                                    results[key] = {"bid": bid.strip(), "ask": ask.strip()}
                                    logger.info(f"Found {target_name}: Bid={bid}")
                    
                    # 检查是否抓取到了核心数据
                    if results:
                        prices_cache["data"] = results
                        prices_cache["status"] = "success"
                        prices_cache["last_updated"] = datetime.now().isoformat()
                        prices_cache["ready"] = True
                        prices_cache["error_log"] = None
                        logger.info("V10-B Scrape successful.")
                    else:
                        raise Exception("No matching price items found. Table structure might have changed.")
                        
                except Exception as e:
                    logger.error(f"Scrape iteration failed: {e}")
                    prices_cache["status"] = "error"
                    prices_cache["error_log"] = str(e)
                
                await browser.close()
                # 每 60 秒抓取一次
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Critical engine error (V10-B): {e}")
            await asyncio.sleep(20)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_scraper())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "version": "V10-B-ULTRA", 
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
