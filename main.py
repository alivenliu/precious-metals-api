import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from playwright.async_api import async_playwright
from datetime import datetime

# Setup explicit logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("profinance-api")

# Global cache for prices
prices_cache = {
    "data": {},
    "status": "initializing",
    "last_updated": None,
    "ready": False
}

async def scrape_prices_loop():
    """Background task with robust error handling and persistence."""
    logger.info("Background scraping loop starting...")
    while True:
        playwright = None
        browser = None
        try:
            playwright = await async_playwright().start()
            logger.info("Playwright started. Launching Chromium...")
            browser = await playwright.chromium.launch(
                headless=True, 
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            while True:
                try:
                    page = await context.new_page()
                    logger.info("Accessing profinance.ru...")
                    await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_selector("#gold", timeout=20000)
                    
                    ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
                    results = {}
                    for item_id in ids:
                        try:
                            bid = await page.locator(f"#{item_id} .quote__row__cell--bid").inner_text()
                            ask = await page.locator(f"#{item_id} .quote__row__cell--ask").inner_text()
                            results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                        except:
                            results[item_id] = {"bid": "N/A", "ask": "N/A"}
                    
                    prices_cache["data"] = results
                    prices_cache["status"] = "success"
                    prices_cache["last_updated"] = datetime.now().isoformat()
                    prices_cache["ready"] = True
                    logger.info(f"Update successful: {list(results.keys())}")
                    
                    await page.close()
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Iteration error: {e}")
                    await asyncio.sleep(10)
                    break # Break inner loop to recreate browser if needed
        except Exception as e:
            logger.error(f"Global scraper error: {e}")
            await asyncio.sleep(10)
        finally:
            if browser:
                try: await browser.close()
                except: pass
            if playwright:
                try: await playwright.stop()
                except: pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API starting up...")
    task = asyncio.create_task(scrape_prices_loop())
    yield
    logger.info("API shutting down...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

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
