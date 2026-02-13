import asyncio
import logging
import os
import sys
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI
from datetime import datetime
from contextlib import asynccontextmanager

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [V9-LIGHT] %(levelname)s: %(message)s',
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

async def fetch_prices():
    """使用轻量级 HTTP 请求获取数据"""
    url = "https://www.profinance.ru/quotes/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            logger.info("Sending HTTP request to profinance.ru...")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
            results = {}
            
            for item_id in ids:
                row = soup.find(id=item_id)
                if row:
                    try:
                        # 在 profinance.ru 的源码中，bid/ask 通常在特定的 class 中
                        bid = row.find(class_='quote__row__cell--bid').get_text(strip=True)
                        ask = row.find(class_='quote__row__cell--ask').get_text(strip=True)
                        results[item_id] = {"bid": bid, "ask": ask}
                    except Exception as e:
                        logger.warning(f"Parse error for {item_id}: {e}")
                        results[item_id] = {"bid": "N/A", "ask": "N/A"}
                else:
                    logger.warning(f"ID {item_id} not found in HTML")
                    results[item_id] = {"bid": "N/A", "ask": "N/A"}
            
            if any(v["bid"] != "N/A" for v in results.values()):
                prices_cache["data"] = results
                prices_cache["status"] = "success"
                prices_cache["last_updated"] = datetime.now().isoformat()
                prices_cache["ready"] = True
                prices_cache["error_log"] = None
                logger.info(f"Update successful. Gold: {results.get('gold')}")
            else:
                raise Exception("Failed to extract any valid price data from HTML")

    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        prices_cache["status"] = "error"
        prices_cache["error_log"] = str(e)

async def scraper_loop():
    """持续抓取循环"""
    while True:
        await fetch_prices()
        # 每 30 秒更新一次
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("V9 Service Starting...")
    task = asyncio.create_task(scraper_loop())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "version": "V9-Light",
        "ready": prices_cache["ready"],
        "status": prices_cache["status"],
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
