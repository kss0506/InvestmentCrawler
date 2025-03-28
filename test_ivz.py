import asyncio
import logging
from scraper import ETFScraper

async def test_ivz():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )
    
    logger = logging.getLogger()
    scraper = ETFScraper()
    
    try:
        # Test a specific ticker
        ticker = "IVZ"
        result = await scraper.get_zum_briefing(ticker)
        
        logger.info(f"Successfully extracted briefing for {ticker}")
        print("\n==================================================")
        print(f"{ticker}:")
        print(result)
        print("==================================================")
    finally:
        scraper.close()

if __name__ == "__main__":
    asyncio.run(test_ivz())