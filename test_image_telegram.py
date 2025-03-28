"""
이미지 변환 및 텔레그램 전송 테스트
"""
import os
import asyncio
import logging
from telegram_sender import send_briefing_as_image, send_html_content

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def test_image_telegram(ticker="IGV", use_text_fallback=True):
    """
    저장된 HTML 파일을 이미지로 변환하여 텔레그램 전송 테스트
    
    Args:
        ticker (str): 테스트할 티커 심볼
        use_text_fallback (bool): 이미지 대신 텍스트로 전송할지 여부
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
    
    # 전송 방식 선택
    if use_text_fallback:
        # 이미지로 시도하고 실패하면 텍스트로 폴백 (기본)
        logger.info(f"{ticker} 브리핑 HTML을 이미지로 변환하여 텔레그램으로 전송...")
        result = await send_briefing_as_image(ticker, html_content)
    else:
        # 곧바로 텍스트로 전송
        logger.info(f"{ticker} 브리핑 HTML을 텍스트로 텔레그램에 전송...")
        result = await send_html_content(ticker, html_content)
    
    if result:
        logger.info(f"{ticker} 브리핑 전송 성공!")
    else:
        logger.error(f"{ticker} 브리핑 전송 실패.")
    
    return result

if __name__ == "__main__":
    # 명령줄 인자로 티커 받기
    import sys
    ticker = "IGV"  # 기본값
    use_text = False  # 기본값: 이미지 모드 (실패시 텍스트로 폴백)
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    
    if len(sys.argv) > 2 and sys.argv[2].lower() == "text":
        # 두번째 인자로 'text'를 입력하면 텍스트 모드로 실행
        use_text = True
        logger.info("텍스트 모드로 실행합니다.")
    
    asyncio.run(test_image_telegram(ticker, use_text_fallback=not use_text))