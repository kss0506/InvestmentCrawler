"""
모든 티커에 대한 이미지 변환 및 텔레그램 전송 테스트
"""
import os
import asyncio
import logging
from config import TICKERS  # 설정된 티커 목록 가져오기
from telegram_sender import send_briefing_as_image

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def test_image_for_ticker(ticker):
    """단일 티커에 대한 이미지 전송 테스트"""
    # 현재 날짜 기준 파일명 생성
    import datetime
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # HTML 파일 경로
    html_file = f"html_outputs/test_{ticker}_{today}.html"
    
    if not os.path.exists(html_file):
        logger.error(f"HTML 파일을 찾을 수 없습니다: {html_file}")
        return False
    
    # HTML 파일 내용 읽기
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # 이미지 변환 및 텔레그램 전송
    logger.info(f"{ticker} 브리핑 HTML을 이미지로 변환하여 텔레그램으로 전송...")
    result = await send_briefing_as_image(ticker, html_content)
    
    if result:
        logger.info(f"{ticker} 브리핑 이미지 전송 성공!")
    else:
        logger.error(f"{ticker} 브리핑 이미지 전송 실패.")
    
    return result

async def test_all_images():
    """모든 티커에 대한 이미지 전송 테스트"""
    logger.info(f"모든 티커 ({len(TICKERS)}개)에 대한 이미지 전송 테스트 시작...")
    
    # 사용자가 지정한 순서대로 테스트: IGV, SOXL, BLK, IVZ, BRKU
    custom_order = ["IGV", "SOXL", "BLK", "IVZ", "BRKU"]
    
    # 지정된 순서의 티커 먼저 처리
    results = []
    for ticker in custom_order:
        if ticker in TICKERS:
            result = await test_image_for_ticker(ticker)
            results.append((ticker, result))
            # 텔레그램 전송 간격 (2초)
            await asyncio.sleep(2)
    
    # 결과 요약
    success_count = sum(1 for _, success in results if success)
    logger.info(f"총 {len(results)}개 중 {success_count}개 성공, {len(results) - success_count}개 실패")
    
    for ticker, success in results:
        status = "성공" if success else "실패"
        logger.info(f"{ticker}: {status}")
    
    return success_count == len(results)

if __name__ == "__main__":
    asyncio.run(test_all_images())