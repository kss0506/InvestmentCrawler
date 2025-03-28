"""
Scheduler module for running ETF scraper at specified times
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta

import schedule

from config import SCHEDULE_HOUR, SCHEDULE_MINUTE, TICKERS
from scraper import ETFScraper

logger = logging.getLogger(__name__)

class ETFScraperScheduler:
    """
    Scheduler for running ETF scraper on a daily schedule
    """
    def __init__(self, tickers=None):
        """
        Initialize the scheduler
        
        Args:
            tickers (list, optional): List of tickers to scrape. Defaults to config.TICKERS.
        """
        self.tickers = tickers or TICKERS
        self.scraper = None
        
    async def run_scraper(self):
        """
        Run the scraper for all configured tickers
        """
        logger.info(f"Starting scheduled scraping task at {datetime.now()}")
        
        try:
            self.scraper = ETFScraper()
            results = await self.scraper.scrape_all_tickers(self.tickers)
            
            # Print all results
            print("\n" + "="*50)
            print(f"ETF DAILY BRIEFINGS - {datetime.now().strftime('%Y-%m-%d')}")
            print("="*50)
            for result in results:
                print(f"\n{result}")
                print("-"*50)
                
            logger.info(f"Completed scraping task for {len(self.tickers)} tickers")
            
        except Exception as e:
            logger.error(f"Error running scheduled task: {e}")
        finally:
            if self.scraper:
                self.scraper.close()
                self.scraper = None
    
    def schedule_daily_run(self):
        """
        Schedule daily execution at the configured time
        """
        logger.info(f"Scheduling daily run at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}")
        
        # Schedule the job to run daily at specified time
        schedule.every().day.at(f"{SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}").do(
            lambda: asyncio.run(self.run_scraper())
        )
        
        # Also run immediately for the first time
        logger.info("Running initial scraping job")
        asyncio.run(self.run_scraper())
        
    def run_continuously(self):
        """
        Run the scheduler continuously
        """
        logger.info("Starting scheduler")
        
        try:
            while True:
                schedule.run_pending()
                
                # Calculate time until next scheduled run
                next_run = schedule.next_run()
                if next_run:
                    now = datetime.now()
                    time_until_next = next_run - now
                    hours, remainder = divmod(time_until_next.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    logger.info(f"Next scheduled run at {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
                               f"(in {hours}h {minutes}m {seconds}s)")
                
                # Sleep for a minute before checking again
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
