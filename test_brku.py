import asyncio
from main import setup_logging
from scraper import ETFScraper

async def test_brku():
    logger = setup_logging()
    scraper = ETFScraper()
    try:
        result = await scraper.get_zum_briefing("BRKU")
        print("\n" + "="*50)
        print(result)
        print("="*50)
    finally:
        scraper.close()

if __name__ == "__main__":
    asyncio.run(test_brku())
