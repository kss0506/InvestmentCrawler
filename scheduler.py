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
from telegram_sender import send_message, send_html_content, send_chart_analysis
from stock_data import get_stock_data

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
            
            try:
                # Use a timeout for the entire scraping operation (2 minutes)
                results = await asyncio.wait_for(
                    self.scraper.scrape_all_tickers(self.tickers),
                    timeout=120
                )
                
                # Print all results
                print("\n" + "="*50)
                print(f"ETF DAILY BRIEFINGS - {datetime.now().strftime('%Y-%m-%d')}")
                print("="*50)
                for result in results:
                    print(f"\n{result}")
                    print("-"*50)
                    
                logger.info(f"Completed scraping task for {len(self.tickers)} tickers")
                
                # 텔레그램으로 전송
                try:
                    logger.info("텔레그램으로 메시지 전송 시작")
                    today_date = datetime.now().strftime("%Y년 %m월 %d일")
                    
                    # 헤더 메시지 전송
                    header_message = f"📊 <b>ETF 데일리 브리핑 ({today_date})</b>\n\n"
                    await send_message(header_message)
                    
                    # 각 ETF/주식 브리핑 전송
                    for result in results:
                        # 티커 추출 (결과의 첫 부분은 항상 "TICKER:"로 시작)
                        ticker = result.split(':')[0].strip()
                        
                        # HTML 콘텐츠 가져오기 (스크래핑된 결과)
                        html_content = result.replace(f"{ticker}:", "")
                        await send_html_content(ticker, html_content)
                        
                        # 차트 분석 데이터 가져오기 및 전송
                        try:
                            chart_data = get_stock_data(ticker)
                            if chart_data:
                                await send_chart_analysis(ticker, chart_data)
                        except Exception as e:
                            logger.error(f"차트 데이터 전송 실패 ({ticker}): {e}")
                        
                        # 각 티커 사이에 약간의 시간 간격 추가
                        await asyncio.sleep(1)
                        
                    logger.info("텔레그램 메시지 전송 완료")
                    
                except Exception as e:
                    logger.error(f"텔레그램 메시지 전송 중 오류 발생: {e}")
                
            except asyncio.TimeoutError:
                logger.error("Overall scraping operation timed out in scheduled run")
                # Generate fallback results for all tickers
                results = []
                for ticker in self.tickers:
                    is_etf = ticker in ['IGV', 'SOXL', 'BRKU']
                    ticker_type = 'etf' if is_etf else 'stock'
                    fallback = f"{ticker}:\n데일리 브리핑\n\n시간 초과로 인해 브리핑을 가져오지 못했습니다. 수동으로 확인해주세요: https://invest.zum.com/{ticker_type}/{ticker}/"
                    results.append(fallback)
                    
                # Print fallback results
                print("\n" + "="*50)
                print(f"ETF DAILY BRIEFINGS - FALLBACK RESULTS - {datetime.now().strftime('%Y-%m-%d')}")
                print("="*50)
                for result in results:
                    print(f"\n{result}")
                    print("-"*50)
                
                logger.info("Printed fallback results due to timeout")
                
                # 텔레그램으로 오류 알림 전송
                try:
                    logger.info("텔레그램으로 타임아웃 알림 전송")
                    today_date = datetime.now().strftime("%Y년 %m월 %d일")
                    
                    # 오류 메시지 전송
                    error_message = (
                        f"⚠️ <b>ETF 데일리 브리핑 오류 ({today_date})</b>\n\n"
                        f"스크래핑 작업 중 타임아웃이 발생했습니다. "
                        f"일부 ETF/주식 정보를 가져오지 못했을 수 있습니다.\n\n"
                        f"영향받은 티커: {', '.join(self.tickers)}"
                    )
                    await send_message(error_message)
                    
                    # 각 티커에 대한 대체 메시지 전송
                    for result in results:
                        ticker = result.split(':')[0].strip()
                        await send_message(result)
                        
                    logger.info("텔레그램 타임아웃 알림 전송 완료")
                    
                except Exception as e:
                    logger.error(f"텔레그램 타임아웃 알림 전송 중 오류 발생: {e}")
            
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
