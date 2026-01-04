import asyncio
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
import uvicorn
import traceback

app = FastAPI(title="Precious Metals Real-time Price API")

async def fetch_prices():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # Navigate to the target URL
            await page.goto("https://www.profinance.ru/quotes/", wait_until="domcontentloaded", timeout=30000)
            
            # Wait for the data to populate
            await page.wait_for_selector(".quote__row", timeout=10000)
            await asyncio.sleep(5) 
            
            # Execute the scraping logic
            print("Scraping...")
            prices = await page.evaluate("""
                () => {
                    const rows = Array.from(document.querySelectorAll('.quote__row'));
                    return rows.map(row => {
                        const nameEl = row.querySelector('.quote__row__cell--name');
                        const bidEl = row.querySelector('.quote__row__cell--bid');
                        const askEl = row.querySelector('.quote__row__cell--ask');
                        return {
                            name: nameEl ? nameEl.innerText.trim() : null,
                            bid: bidEl ? bidEl.innerText.trim() : null,
                            ask: askEl ? askEl.innerText.trim() : null
                        };
                    }).filter(r => r.name && ['Gold', 'Silver', 'Platinum', 'Palladium'].includes(r.name));
                }
            """)
            
            await browser.close()
            print(f"Scraped prices: {prices}")
            
            # Convert to a more friendly format
            result = {}
            for item in prices:
                result[item['name'].lower()] = {
                    "bid": float(item['bid'].replace(',', '')) if item['bid'] else None,
                    "offer": float(item['ask'].replace(',', '')) if item['ask'] else None
                }
            return result
        except Exception as e:
            await browser.close()
            raise e

@app.get("/prices")
async def get_prices():
    try:
        data = await fetch_prices()
        if not data:
            raise HTTPException(status_code=500, detail="Could not fetch prices")
        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
