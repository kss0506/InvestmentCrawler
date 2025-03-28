"""
Main module for ETF Daily Briefing Scraper
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, TICKERS, TEST_TICKERS
from scheduler import ETFScraperScheduler
from scraper import ETFScraper
from telegram_sender import send_message, send_html_content, send_chart_analysis, send_briefing_as_image
from stock_data import get_stock_data

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
                    
                    # 브리핑 내용을 이미지로 변환하여 전송
                    await send_briefing_as_image(ticker, html_content)
                    
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
                
            # 텔레그램으로 오류 알림 전송
            try:
                logger.info("텔레그램으로 타임아웃 알림 전송")
                today_date = datetime.now().strftime("%Y년 %m월 %d일")
                
                # 오류 메시지 전송
                error_message = (
                    f"⚠️ <b>ETF 데일리 브리핑 오류 ({today_date})</b>\n\n"
                    f"스크래핑 작업 중 타임아웃이 발생했습니다. "
                    f"일부 ETF/주식 정보를 가져오지 못했을 수 있습니다.\n\n"
                    f"영향받은 티커: {', '.join(tickers)}"
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
