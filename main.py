"""
Main module for ETF Daily Briefing Scraper
"""
import asyncio
import logging
import sys
import os

from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, TICKERS
from scheduler import ETFScraperScheduler
from scraper import ETFScraper

def setup_logging():
    """
    Configure logging for the application
    """
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
            logging.FileHandler(LOG_FILE)
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    return logger

async def run_once(tickers=None):
    """
    Run the scraper once for all specified tickers
    
    Args:
        tickers (list, optional): List of ticker symbols. Defaults to config.TICKERS.
    """
    tickers = tickers or TICKERS
    logger.info(f"Running one-time scrape for tickers: {', '.join(tickers)}")
    
    scraper = None
    try:
        scraper = ETFScraper()
        results = await scraper.scrape_all_tickers(tickers)
        
        # Print all results
        print("\n" + "="*50)
        print(f"ETF DAILY BRIEFINGS - SINGLE RUN")
        print("="*50)
        for result in results:
            print(f"\n{result}")
            print("-"*50)
            
    except Exception as e:
        logger.error(f"Error in one-time scrape: {e}")
    finally:
        if scraper:
            scraper.close()

def run_scheduled():
    """
    Run the scraper on a daily schedule
    """
    logger.info("Starting scheduled scraper")
    scheduler = ETFScraperScheduler(tickers=TICKERS)
    scheduler.schedule_daily_run()
    scheduler.run_continuously()

if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()
    logger.info("Starting ETF Daily Briefing Scraper")
    
    # Check if run mode is specified as environment variable
    run_mode = os.environ.get("RUN_MODE", "scheduled").lower()
    
    if run_mode == "single":
        # Run once for specified tickers
        asyncio.run(run_once())
    else:
        # Default to scheduled mode
        run_scheduled()
