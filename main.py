import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for prices
prices_cache = {
    "data": {},
    "status": "initializing",
    "last_updated": None
}

async def scrape_prices():
    """Background task to scrape prices periodically."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        while True:
            try:
                page = await context.new_page()
                logger.info("Scraping prices from profinance.ru...")
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
                from datetime import datetime
                prices_cache["last_updated"] = datetime.now().isoformat()
                logger.info("Prices updated successfully.")
                
                await page.close()
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                prices_cache["status"] = f"error: {str(e)}"
                print(f"DEBUG ERROR: {e}")
            
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
async def root():
    return {"message": "ProFinance Price API is running", "endpoints": ["/prices"]}

@app.get("/prices")
async def get_prices():
    return prices_cache

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
