"""
이미지 변환 및 텔레그램 전송 테스트
"""
import os
import asyncio
import logging
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

async def test_image_telegram(ticker="IGV"):
    """
    저장된 HTML 파일을 이미지로 변환하여 텔레그램 전송 테스트
    """
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

if __name__ == "__main__":
    # 명령줄 인자로 티커 받기
    import sys
    ticker = "IGV"  # 기본값
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    
    asyncio.run(test_image_telegram(ticker))