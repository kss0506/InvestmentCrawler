"""
Main module for ETF Daily Briefing Scraper
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

from flask import Flask, jsonify
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, TICKERS, TEST_TICKERS
from scraper import ETFScraper
from telegram_sender import send_message, send_html_content, send_chart_analysis
from stock_data import get_stock_data

# Initialize Flask app
app = Flask(__name__)

def setup_logging():
    """Configure logging for the application"""
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
    """Run scraper once for testing"""
    if logger is None:
        logger = setup_logging()
    return await run_scraper(tickers, logger)

async def run_scraper(tickers=None, logger=None):
    """Run the scraper for specified tickers"""
    if logger is None:
        logger = setup_logging()

    # 지정된 순서로 티커 정렬
    default_order = ["IGV", "SOXL", "BLK", "IVZ", "BRKU"]
    if tickers is None:
        tickers = default_order
    else:
        # 입력된 티커들을 지정된 순서대로 정렬
        tickers = sorted(tickers, key=lambda x: default_order.index(x) if x in default_order else len(default_order))
    
    logger.info(f"Running scrape for tickers: {', '.join(tickers)}")

    scraper = None
    try:
        scraper = ETFScraper()
        results = await asyncio.wait_for(
            scraper.scrape_all_tickers(tickers),
            timeout=120
        )

        # Send to Telegram
        try:
            logger.info("텔레그램으로 메시지 전송 시작")
            today_date = datetime.now().strftime("%Y년 %m월 %d일")

            header_message = f"📊 <b>ETF 데일리 브리핑 ({today_date})</b>\n\n"
            await send_message(header_message)

            for result in results:
                ticker = result.split(':')[0].strip()
                html_content = result.replace(f"{ticker}:", "")

                await send_html_content(ticker, html_content)

                try:
                    chart_data = get_stock_data(ticker)
                    if chart_data:
                        await send_chart_analysis(ticker, chart_data)
                except Exception as e:
                    logger.error(f"차트 데이터 전송 실패 ({ticker}): {e}")

                await asyncio.sleep(1)

            logger.info("텔레그램 메시지 전송 완료")
            return True

        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 중 오류 발생: {e}")
            return False

    except asyncio.TimeoutError:
        logger.error("Overall scraping operation timed out")
        # Generate fallback results for all tickers
        results = []
        for ticker in tickers:
            fallback = f"{ticker}:\n데일리 브리핑\n\n시간 초과로 인해 브리핑을 가져오지 못했습니다. 수동으로 확인해주세요: https://invest.zum.com/{'etf' if ticker in ['IGV', 'SOXL', 'BRKU'] else 'stock'}/{ticker}/"
            results.append(fallback)

        # Send fallback message to Telegram
        try:
            logger.info("텔레그램으로 타임아웃 알림 전송")
            today_date = datetime.now().strftime("%Y년 %m월 %d일")

            error_message = (
                f"⚠️ <b>ETF 데일리 브리핑 오류 ({today_date})</b>\n\n"
                f"스크래핑 작업 중 타임아웃이 발생했습니다. "
                f"일부 ETF/주식 정보를 가져오지 못했을 수 있습니다.\n\n"
                f"영향받은 티커: {', '.join(tickers)}"
            )
            await send_message(error_message)

            for result in results:
                ticker = result.split(':')[0].strip()
                await send_message(result)

            logger.info("텔레그램 타임아웃 알림 전송 완료")

        except Exception as e:
            logger.error(f"텔레그램 타임아웃 알림 전송 중 오류 발생: {e}")
        return False

    except Exception as e:
        logger.error(f"Error in scrape: {e}")
        return False
    finally:
        if scraper:
            scraper.close()

@app.route('/trigger-scrape', methods=['POST'])
async def trigger_scrape():
    """HTTP endpoint to trigger ETF scraping"""
    logger = setup_logging()
    success = await run_scraper(logger=logger)

    return jsonify({
        'success': success,
        'timestamp': datetime.now().isoformat(),
        'message': 'Scraping completed successfully' if success else 'Scraping failed'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Starting ETF Daily Briefing Scraper")
    app.run(host='0.0.0.0', port=5000)