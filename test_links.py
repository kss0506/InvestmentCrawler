"""
링크 추출 기능 테스트
"""
import asyncio
import logging
from scraper import ETFScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

async def test_extract_links(ticker):
    """링크 추출 테스트"""
    scraper = None
    try:
        scraper = ETFScraper()
        logger.info(f"Testing link extraction for {ticker}")
        
        # URL 로드 먼저 수행
        if ticker in ["BLK", "IVZ"]:
            url = f"https://invest.zum.com/stock/{ticker}/"
        else:
            url = f"https://invest.zum.com/etf/{ticker}/"
            
        logger.info(f"Loading URL: {url}")
        scraper.driver.get(url)
        
        # 페이지 로딩 대기
        logger.info("Waiting for page to load...")
        await asyncio.sleep(5)
        
        # 링크 추출 시도
        links = scraper.extract_news_links(ticker)
        logger.info(f"Found {len(links)} links for {ticker}")
        
        # 링크 출력 (최대 5개만)
        for i, link in enumerate(links[:5]):
            logger.info(f"Link {i+1}: {link}")
            
        return links
    finally:
        if scraper:
            scraper.close()

async def main():
    """메인 테스트 함수"""
    tickers = ["IGV", "BLK"]
    
    for ticker in tickers:
        await test_extract_links(ticker)

if __name__ == "__main__":
    asyncio.run(main())