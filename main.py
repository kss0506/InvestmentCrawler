"""
Main module for ETF Daily Briefing Scraper
"""
import asyncio
import logging
import sys
import os

from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, TICKERS, TEST_TICKERS
from scheduler import ETFScraperScheduler
from scraper import ETFScraper

# Import Flask app for Gunicorn
from app import app

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

async def run_once(tickers=None, logger=None):
    """
    Run the scraper once for all specified tickers
    
    Args:
        tickers (list, optional): List of ticker symbols. Defaults to config.TICKERS.
        logger (Logger, optional): Logger instance. If None, creates a new one.
    """
    if logger is None:
        logger = setup_logging()
        
    tickers = tickers or TICKERS
    logger.info(f"Running one-time scrape for tickers: {', '.join(tickers)}")
    
    scraper = None
    try:
        # Add overall timeout for the entire process
        scraper = ETFScraper()
        
        try:
            # Use a timeout for the entire scraping operation (2 minutes)
            results = await asyncio.wait_for(
                scraper.scrape_all_tickers(tickers),
                timeout=120
            )
            
            # Print all results
            print("\n" + "="*50)
            print(f"ETF DAILY BRIEFINGS - SINGLE RUN")
            print("="*50)
            for result in results:
                print(f"\n{result}")
                print("-"*50)
                
        except asyncio.TimeoutError:
            logger.error("Overall scraping operation timed out")
            # Generate fallback results for all tickers
            results = []
            for ticker in tickers:
                fallback = f"{ticker}:\n데일리 브리핑\n\n시간 초과로 인해 브리핑을 가져오지 못했습니다. 수동으로 확인해주세요: https://invest.zum.com/{'etf' if ticker in ['IGV', 'SOXL', 'BRKU'] else 'stock'}/{ticker}/"
                results.append(fallback)
                
            # Print fallback results
            print("\n" + "="*50)
            print(f"ETF DAILY BRIEFINGS - FALLBACK RESULTS")
            print("="*50)
            for result in results:
                print(f"\n{result}")
                print("-"*50)
            
    except Exception as e:
        logger.error(f"Error in one-time scrape: {e}")
    finally:
        if scraper:
            scraper.close()

def run_scheduled(logger=None):
    """
    Run the scraper on a daily schedule
    
    Args:
        logger (Logger, optional): Logger instance. If None, creates a new one.
    """
    if logger is None:
        logger = setup_logging()
        
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
        asyncio.run(run_once(logger=logger))
    elif run_mode == "test":
        # Run once with test tickers (BLK only)
        logger.info("Running in test mode with limited tickers")
        asyncio.run(run_once(tickers=TEST_TICKERS, logger=logger))
    else:
        # Default to scheduled mode
        run_scheduled(logger=logger)
