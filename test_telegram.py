"""
텔레그램 봇 기능 테스트
"""
import asyncio
import logging
import os
from datetime import datetime

import telegram_sender

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

async def test_telegram():
    """텔레그램 봇 연결 및 메시지 전송 테스트"""
    logger.info("텔레그램 봇 테스트 시작")
    
    # 텔레그램 봇 상태 확인
    status = await telegram_sender.check_telegram_status()
    logger.info(f"텔레그램 봇 상태: {status}")
    
    # 간단한 HTML 메시지 전송 테스트
    current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
    test_html = f"""
    <b>ETF 데일리 브리핑 테스트</b>
    
    테스트 시간: {current_time}
    
    <u>테스트 항목</u>
    ✅ 텔레그램 봇 연결
    ✅ HTML 형식 메시지 전송
    ✅ 한글 지원 테스트
    
    <i>스크래퍼가 정상적으로 작동 중입니다.</i>
    """
    
    # HTML 형식으로 메시지 전송
    success = await telegram_sender.send_message(test_html)
    
    if success:
        logger.info("테스트 메시지 전송 성공")
    else:
        logger.error("테스트 메시지 전송 실패")
    
    # 텍스트 이미지 전송 테스트
    logger.info("텍스트를 이미지로 변환하여 전송 테스트")
    sample_briefing = f"""
    <b>블랙록(BLK) 데일리 브리핑</b>
    
    2025년 3월 28일, 블랙록 주식이 1.5% 상승하여 878.42달러에 마감했습니다. 
    글로벌 ETF 시장에서 선두를 유지하고 있는 블랙록은 최근 AI 관련 투자 전략과 
    ESG(Environmental, Social, and Governance) 분야에서의 성장이 주목받고 있습니다.
    
    다음은 관련 뉴스입니다:
    - 블랙록, 새로운 AI 투자 전략 발표 https://example.com/news1
    - 이번 분기 실적 예상치 초과 전망 https://example.com/news2
    - ESG ETF 시장 점유율 확대 https://example.com/news3
    
    <i>참고: 이 내용은 테스트를 위한 샘플 데이터입니다.</i>
    """
    
    image_success = await telegram_sender.send_briefing_as_image("BLK", sample_briefing)
    
    if image_success:
        logger.info("텍스트 이미지 전송 성공")
    else:
        logger.error("텍스트 이미지 전송 실패")
    
    # 간단한 차트 분석 데이터 테스트
    test_chart_data = {
        "ticker": "BLK",
        "current_price": 873.42,
        "change_percent": 1.23,
        "moving_avg_50": 850.15,
        "moving_avg_200": 810.72,
        "max_52w": 890.20,
        "min_52w": 750.30
    }
    
    # 차트 분석 데이터 전송
    chart_success = await telegram_sender.send_chart_analysis("BLK", test_chart_data)
    
    if chart_success:
        logger.info("차트 분석 데이터 전송 성공")
    else:
        logger.error("차트 분석 데이터 전송 실패")
    
    return success

if __name__ == "__main__":
    asyncio.run(test_telegram())