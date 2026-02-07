import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from playwright.async_api import async_playwright
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global cache for prices
prices_cache = {
    "data": {},
    "status": "waiting_for_first_run",
    "last_updated": None,
    "ready": False,
    "error_count": 0
}

async def scrape_prices_loop():
    """Background task to scrape prices periodically with improved error handling."""
    logger.info("Background task started.")
    playwright = None
    browser = None
    
    while True:
        try:
            if not playwright:
                playwright = await async_playwright().start()
            
            if not browser:
                logger.info("Launching Chromium...")
                browser = await playwright.chromium.launch(
                    headless=True, 
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            logger.info("Fetching data from profinance.ru...")
            
            # Navigate with a reasonable timeout
            await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector("#gold", timeout=15000)
            
            ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
            results = {}
            
            for item_id in ids:
                try:
                    bid = await page.locator(f"#{item_id} .quote__row__cell--bid").inner_text()
                    ask = await page.locator(f"#{item_id} .quote__row__cell--ask").inner_text()
                    results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                except Exception as e:
                    results[item_id] = {"error": "not_found_on_page"}
            
            prices_cache["data"] = results
            prices_cache["status"] = "success"
            prices_cache["last_updated"] = datetime.now().isoformat()
            prices_cache["ready"] = True
            prices_cache["error_count"] = 0
            logger.info("Prices updated successfully.")
            
            await context.close()
            
        except Exception as e:
            logger.error(f"Scraping iteration failed: {e}")
            prices_cache["status"] = f"error: {str(e)}"
            prices_cache["error_count"] += 1
            
            # If browser crashed, try to reset it next time
            if browser:
                try:
                    await browser.close()
                except:
                    pass
                browser = None
            
            # Wait a bit before retrying if it failed
            await asyncio.sleep(10)
            continue
            
        # Success wait
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # The background task starts AFTER the server has bound to the port
    task = asyncio.create_task(scrape_prices_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    # Return 200 immediately to satisfy Railway healthcheck
    return {
        "service": "ProFinance Price API",
        "up": True,
        "ready": prices_cache["ready"],
        "last_updated": prices_cache["last_updated"]
    }

@app.get("/prices")
async def get_prices():
    return prices_cache

@app.get("/health")
async def health(response: Response):
    # Simple health check
    return {"status": "ok", "ready": prices_cache["ready"]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
