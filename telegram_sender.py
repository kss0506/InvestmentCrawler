"""
텔레그램 메시지 전송 모듈 - ETF 데일리 브리핑 자동 전송
"""
import os
import logging
import re
import asyncio
import aiohttp
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime
from matplotlib.dates import DateFormatter, MonthLocator

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("telegram_sender.log")
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수에서 토큰과 채팅 ID 가져오기
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


async def send_message(message_text, parse_mode='HTML'):
    """
    텔레그램으로 메시지 전송 - HTTP API 직접 사용
    
    Args:
        message_text (str): 전송할 메시지 텍스트
        parse_mode (str, optional): 메시지 파싱 모드 ('HTML', 'Markdown', None). 기본값: 'HTML'
        
    Returns:
        bool: 성공 여부
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다.")
        return False
    
    # 텔레그램 API URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # 요청 데이터 - 챗_ID 형변환 (숫자값으로 간주)
    try:
        chat_id = int(CHAT_ID)
    except ValueError:
        # 문자열로 그대로 사용 (채널명, 사용자명 등)
        chat_id = CHAT_ID
        
    payload = {
        "chat_id": chat_id,
        "text": message_text
    }
    
    # parse_mode 설정 (필요한 경우만)
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        logger.info(f"텔레그램 메시지 전송 성공 (채팅 ID: {CHAT_ID})")
                        return True
                    else:
                        logger.error(f"텔레그램 API 오류: {result.get('description')}")
                else:
                    # 응답 내용 확인하여 로깅
                    try:
                        error_content = await response.text()
                        logger.error(f"텔레그램 API 응답 오류. 상태 코드: {response.status}, 내용: {error_content}")
                    except:
                        logger.error(f"텔레그램 API 응답 오류. 상태 코드: {response.status}")
                
                # HTML 모드에서 실패하면 텍스트 모드로 재시도
                if parse_mode == 'HTML':
                    logger.info("HTML 파싱 모드 실패, 일반 텍스트로 재시도")
                    # HTML 태그 제거
                    clean_text = re.sub(r'<[^>]*>', '', message_text)
                    
                    # 요청 데이터 업데이트
                    payload = {
                        "chat_id": chat_id,  # 이미 변환된 chat_id 사용
                        "text": clean_text
                    }
                    
                    async with session.post(url, json=payload) as retry_response:
                        if retry_response.status == 200:
                            retry_result = await retry_response.json()
                            if retry_result.get("ok"):
                                logger.info("텍스트 모드로 메시지 전송 성공")
                                return True
                        
                        try:
                            retry_error = await retry_response.text()
                            logger.error(f"텍스트 모드 재시도도 실패. 응답: {retry_error}")
                        except:
                            logger.error("텍스트 모드 재시도도 실패")
                return False
                
    except Exception as e:
        logger.error(f"텔레그램 메시지 전송 중 예외 발생: {e}")
        return False


async def send_html_content(ticker, html_content):
    """
    HTML 콘텐츠를 텔레그램 메시지로 변환하여 전송
    
    Args:
        ticker (str): 티커 심볼
        html_content (str): HTML 내용
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 메시지 제목 생성
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        message_title = f"📊 <b>{ticker} 데일리 브리핑</b> ({current_date})\n\n"
        
        # HTML에서 필요한 내용 추출 (이 부분은 HTML 구조에 따라 수정 필요)
        # 여기서는 간단한 예시만 포함
        message_body = html_content.replace("<br>", "\n")
        message_body = message_body.replace("<p>", "").replace("</p>", "\n")
        message_body = message_body.replace("<b>", "<b>").replace("</b>", "</b>")
        message_body = message_body.replace("<strong>", "<b>").replace("</strong>", "</b>")
        
        # HTML 태그 제거 (나머지 모든 태그)
        import re
        message_body = re.sub(r'<[^>]*>', '', message_body)
        
        # 메시지 조합
        full_message = message_title + message_body
        
        # 긴 메시지 처리 (텔레그램 제한: 4096자)
        if len(full_message) > 4000:
            chunks = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
            success = True
            for i, chunk in enumerate(chunks):
                # 첫 번째 청크에는 제목 포함, 나머지는 '계속' 표시
                if i > 0:
                    chunk = f"(계속) {chunk}"
                chunk_success = await send_message(chunk)
                success = success and chunk_success
            return success
        else:
            return await send_message(full_message)
    except Exception as e:
        logger.error(f"메시지 변환 및 전송 실패: {e}")
        return False


async def send_photo(photo_bytes, caption=None, parse_mode=None):
    """
    텔레그램으로 이미지 전송
    
    Args:
        photo_bytes (bytes): 이미지 바이트 데이터
        caption (str, optional): 이미지 설명
        parse_mode (str, optional): 캡션 파싱 모드 ('HTML', 'Markdown', None)
        
    Returns:
        bool: 성공 여부
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다.")
        return False
    
    # 텔레그램 API URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    # 요청 데이터 - 챗_ID 형변환 (숫자값으로 간주)
    try:
        chat_id = int(CHAT_ID)
    except ValueError:
        # 문자열로 그대로 사용 (채널명, 사용자명 등)
        chat_id = CHAT_ID
    
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('chat_id', str(chat_id))
            form.add_field('photo', photo_bytes, filename='chart.png', content_type='image/png')
            
            if caption:
                form.add_field('caption', caption)
            
            if parse_mode:
                form.add_field('parse_mode', parse_mode)
            
            async with session.post(url, data=form) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        logger.info(f"텔레그램 이미지 전송 성공 (채팅 ID: {CHAT_ID})")
                        return True
                    else:
                        logger.error(f"텔레그램 API 오류: {result.get('description')}")
                else:
                    # 응답 내용 확인하여 로깅
                    try:
                        error_content = await response.text()
                        logger.error(f"텔레그램 API 응답 오류. 상태 코드: {response.status}, 내용: {error_content}")
                    except:
                        logger.error(f"텔레그램 API 응답 오류. 상태 코드: {response.status}")
                return False
    except Exception as e:
        logger.error(f"텔레그램 이미지 전송 중 예외 발생: {e}")
        return False


def create_stock_chart(ticker, data):
    """
    주식/ETF 차트 이미지 생성
    
    Args:
        ticker (str): 티커 심볼
        data (dict): 차트 데이터
        
    Returns:
        bytes: 이미지 바이트 데이터
    """
    try:
        # 데이터 준비
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in data.get('dates', [])]
        prices = data.get('prices', [])
        ma50 = data.get('ma50', [])
        ma200 = data.get('ma200', [])
        
        # 차트 크기 설정
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')  # 다크모드 테마
        
        # 가격 그래프
        plt.plot(dates, prices, color='#00BFFF', linewidth=2, label='가격')
        
        # 이동평균선
        valid_ma50 = [(d, p) for d, p in zip(dates, ma50) if p is not None]
        if valid_ma50:
            ma50_dates, ma50_values = zip(*valid_ma50)
            plt.plot(ma50_dates, ma50_values, color='#FFD700', linewidth=1.5, label='50일 이동평균')
        
        valid_ma200 = [(d, p) for d, p in zip(dates, ma200) if p is not None]
        if valid_ma200:
            ma200_dates, ma200_values = zip(*valid_ma200)
            plt.plot(ma200_dates, ma200_values, color='#FF4500', linewidth=1.5, label='200일 이동평균')
        
        # 그래프 스타일 설정
        plt.grid(True, alpha=0.3)
        plt.title(f"{ticker} 주가 차트 (1년)", fontsize=16, pad=10)
        plt.ylabel("가격 (USD)", fontsize=12)
        
        # X축 날짜 포맷 설정
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        
        # 범례 표시
        plt.legend()
        plt.tight_layout()
        
        # 이미지를 바이트로 변환
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=100)
        img_buf.seek(0)
        img_bytes = img_buf.getvalue()
        plt.close()
        
        return img_bytes
    except Exception as e:
        logger.error(f"차트 이미지 생성 실패: {e}")
        plt.close()  # 에러 발생해도 figure 닫기
        return None


async def send_chart_analysis(ticker, data):
    """
    차트 분석 결과와 이미지를 텔레그램으로 전송
    
    Args:
        ticker (str): 티커 심볼
        data (dict): 차트 데이터
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 현재 가격과 이동평균선 정보
        current_price = data.get('current_price', 0)
        ma200 = data.get('current_ma200')
        ma200_plus10 = data.get('current_ma200_plus10')
        
        # 메시지 생성
        message = f"📈 <b>{ticker} 차트 분석</b>\n\n"
        message += f"현재 가격: <b>${current_price:.2f}</b>\n"
        
        if ma200:
            message += f"200일 이동평균: <b>${ma200:.2f}</b>\n"
            # 가격이 MA200 위/아래 표시
            if data.get('is_above_ma200', False):
                message += "✅ 현재 가격이 200일 이동평균선 <b>위</b>에 있습니다.\n"
            else:
                message += "⚠️ 현재 가격이 200일 이동평균선 <b>아래</b>에 있습니다.\n"
        
        if ma200_plus10:
            message += f"200일 이동평균 +10%: <b>${ma200_plus10:.2f}</b>\n"
            # 가격이 MA200+10% 위/아래 표시
            if data.get('is_above_ma200_plus10', False):
                message += "🔥 현재 가격이 200일 이동평균 +10% <b>위</b>에 있습니다.\n"
            else:
                message += "📉 현재 가격이 200일 이동평균 +10% <b>아래</b>에 있습니다.\n"
        
        # 텍스트 메시지 먼저 전송
        text_success = await send_message(message)
        
        # 차트 이미지 생성 및 전송
        chart_bytes = create_stock_chart(ticker, data)
        if chart_bytes:
            # 차트 설명 캡션
            caption = f"{ticker} 1년 주가 차트"
            image_success = await send_photo(chart_bytes, caption)
            return text_success and image_success
        
        return text_success
    except Exception as e:
        logger.error(f"차트 분석 메시지 및 이미지 전송 실패: {e}")
        return False


# 텔레그램 봇 상태 확인
async def check_telegram_status():
    """
    텔레그램 봇 상태 확인
    """
    if not BOT_TOKEN:
        logger.error("텔레그램 봇 토큰이 설정되지 않았습니다.")
        return False
        
    # 텔레그램 API URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        bot_info = result.get("result", {})
                        bot_name = bot_info.get("first_name", "Unknown")
                        bot_username = bot_info.get("username", "Unknown")
                        logger.info(f"텔레그램 봇 연결 성공: {bot_name} (@{bot_username})")
                        return True
                    else:
                        logger.error(f"텔레그램 API 오류: {result.get('description')}")
                else:
                    logger.error(f"텔레그램 API 응답 오류. 상태 코드: {response.status}")
                return False
    except Exception as e:
        logger.error(f"텔레그램 봇 상태 확인 중 예외 발생: {e}")
        return False


# 테스트 함수
async def test_telegram():
    """
    텔레그램 연결 테스트
    """
    # 환경 변수 출력 (디버깅용, 실제 값은 로그에 남기지 않음)
    if BOT_TOKEN:
        logger.info("봇 토큰이 설정되어 있습니다.")
    else:
        logger.error("봇 토큰이 설정되어 있지 않습니다.")
        
    if CHAT_ID:
        logger.info(f"채팅 ID가 설정되어 있습니다. (타입: {type(CHAT_ID).__name__})")
    else:
        logger.error("채팅 ID가 설정되어 있지 않습니다.")
    
    # 봇 상태 확인
    bot_status = await check_telegram_status()
    if not bot_status:
        logger.error("텔레그램 봇 상태 확인 실패. 봇 토큰이 유효한지 확인하세요.")
        return False
        
    # 채팅 ID 확인
    if not CHAT_ID:
        logger.error("텔레그램 채팅 ID가 설정되지 않았습니다.")
        return False
        
    # 간단한 텍스트 메시지로 먼저 테스트
    simple_message = "ETF 데일리 브리핑 봇 테스트 메시지"
    # 텍스트 모드는 parse_mode를 지정하지 않음
    simple_result = await send_message(simple_message, parse_mode="")
    
    if simple_result:
        logger.info("간단한 텍스트 메시지 전송 성공")
        
        # HTML 형식 메시지 테스트
        html_message = (
            "🤖 <b>ETF 데일리 브리핑 봇 테스트</b>\n\n"
            "이 메시지는 텔레그램 봇 연결 테스트입니다.\n"
            "매일 아침 9시에 ETF 데일리 브리핑이 이 채팅으로 전송됩니다."
        )
        return await send_message(html_message)
    else:
        logger.error("간단한 텍스트 메시지 전송 실패")
        return False


# 직접 실행 시 테스트 수행
if __name__ == "__main__":
    asyncio.run(test_telegram())