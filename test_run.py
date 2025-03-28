import asyncio
import logging
from main import setup_logging, run_once

async def main():
    """Test run with all tickers"""
    logger = setup_logging()
    await run_once(tickers=["IGV", "SOXL", "BLK", "IVZ", "BRKU"], logger=logger)

if __name__ == "__main__":
    asyncio.run(main())