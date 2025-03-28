"""
텔레그램으로 차트 이미지 전송 테스트
"""
import asyncio
import logging
from stock_data import get_stock_data
from telegram_sender import send_chart_analysis

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

async def test_chart_telegram():
    """차트 생성 및 텔레그램 전송 테스트"""
    logger.info("차트 이미지 텔레그램 전송 테스트 시작")
    
    # 테스트할 티커 - 하나만 실행
    ticker = "BLK"
    
    logger.info(f"{ticker} 차트 데이터 가져오기")
    data = get_stock_data(ticker)
    
    if not data:
        logger.error(f"{ticker} 데이터를 가져오지 못했습니다.")
        return False
        
    logger.info(f"{ticker} 차트 이미지 생성 및 전송")
    success = await send_chart_analysis(ticker, data)
    
    if success:
        logger.info(f"{ticker} 차트 및 분석 전송 성공")
    else:
        logger.error(f"{ticker} 차트 및 분석 전송 실패")
    
    logger.info("차트 이미지 텔레그램 전송 테스트 완료")
    return True

if __name__ == "__main__":
    asyncio.run(test_chart_telegram())