import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from playwright.async_api import async_playwright
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for prices
prices_cache = {
    "data": {},
    "status": "initializing",
    "last_updated": None,
    "ready": False
}

async def scrape_prices():
    """Background task to scrape prices periodically."""
    async with async_playwright() as p:
        logger.info("Launching browser...")
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        while True:
            try:
                page = await context.new_page()
                logger.info("Scraping prices from profinance.ru...")
                # Use a more aggressive wait strategy
                await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector("#gold", timeout=30000)
                
                ids = ['gold', 'silver', 'platinum', 'palladium', 'USDCNY', 'USDCNH']
                results = {}
                
                for item_id in ids:
                    try:
                        bid = await page.locator(f"#{item_id} .quote__row__cell--bid").inner_text()
                        ask = await page.locator(f"#{item_id} .quote__row__cell--ask").inner_text()
                        results[item_id] = {"bid": bid.strip(), "ask": ask.strip()}
                    except Exception as e:
                        logger.error(f"Error scraping {item_id}: {e}")
                        results[item_id] = {"error": str(e)}
                
                prices_cache["data"] = results
                prices_cache["status"] = "success"
                prices_cache["last_updated"] = datetime.now().isoformat()
                prices_cache["ready"] = True
                logger.info("Prices updated successfully.")
                
                await page.close()
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                prices_cache["status"] = f"error: {str(e)}"
                # If we have data from previous runs, we're still "ready"
                if not prices_cache["data"]:
                    prices_cache["ready"] = False
            
            # Wait for 60 seconds before next scrape
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background task
    task = asyncio.create_task(scrape_prices())
    yield
    # Clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root(response: Response):
    # Railway healthcheck will hit this. 
    # We return 200 even if not "ready" yet to prevent Railway from killing the container during boot,
    # but we provide status info.
    return {
        "message": "ProFinance Price API is running", 
        "ready": prices_cache["ready"],
        "status": prices_cache["status"]
    }

@app.get("/prices")
async def get_prices():
    return prices_cache

@app.get("/health")
async def health(response: Response):
    if not prices_cache["ready"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": prices_cache["ready"]}
