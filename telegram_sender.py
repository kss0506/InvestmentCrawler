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
from PIL import Image, ImageDraw, ImageFont
import textwrap
import html

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
        # BeautifulSoup으로 HTML 처리
        from bs4 import BeautifulSoup
        import re
        import html as html_module
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 브리핑 제목 구성 (티커 + 날짜)
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        header = f"📈 <b>{ticker} 데일리 브리핑</b> ({current_date})\n\n"
        
        # 링크 추출
        links = []
        content_section = None
        
        # 주요 콘텐츠 영역 찾기
        for class_name in ['etf-content', 'etf-briefing', 'daily-briefing', 'article', 'content']:
            found = soup.find(class_=lambda x: x and isinstance(x, str) and class_name in x.lower())
            if found:
                content_section = found
                break
                
        # 콘텐츠 영역이 없으면 전체 문서 사용
        target = content_section if content_section else soup
        
        # 링크 추출 및 처리
        link_elements = target.find_all('a', href=True)
        for a in link_elements:
            href = a['href']
            # 상대 경로 링크는 전체 URL로 변환
            if href.startswith('/'):
                href = "https://invest.zum.com" + href
                
            # 앵커 링크나 자바스크립트 링크는 건너뛰기
            elif href.startswith('#') or href.startswith('javascript:'):
                continue
                
            # docid 파라미터가 있는 링크 확인 (뉴스 링크)
            if 'docid=' in href or 'doctype=news' in href:
                # 이미 완전한 URL 형태인지 확인
                if not href.startswith('http'):
                    # 티커 타입에 따라 URL 경로 다르게 구성
                    base_url = f"https://invest.zum.com/{'etf' if ticker not in ['BLK', 'IVZ'] else 'stock'}/{ticker}/"
                    href = f"{base_url}{href}"
                
                # 파라미터 확인 및 추가
                if 'doctype=news' not in href:
                    if '?' in href:
                        href += '&doctype=news'
                    else:
                        href += '?doctype=news'
                        
                if 'docid=' not in href:
                    href += '&docid=5384592'
                    
                if 'isdomestic=' not in href:
                    href += '&isdomestic=false'
                    
                if 'istrending=' not in href:
                    href += '&istrending=false'
                
            # 실제 URL만 포함
            if href.startswith('http'):
                link_text = a.get_text(strip=True) or href
                # 빈 텍스트면 더 깊이 탐색해서 텍스트 추출 시도
                if not link_text or len(link_text) < 3:
                    # 링크 내부 요소들에서 텍스트 더 탐색
                    inner_text = []
                    for elem in a.find_all(text=True):
                        if elem.strip():
                            inner_text.append(elem.strip())
                    if inner_text:
                        link_text = ' '.join(inner_text)
                
                # 너무 긴 링크 텍스트는 자르기
                if len(link_text) > 100:
                    link_text = link_text[:97] + "..."
                    
                # 브리핑 원문 링크 정보 저장
                links.append(f"<a href='{href}'>{link_text}</a>")
                
                # 텍스트에서는 '원문 보기' 표시로 변경
                a.replace_with(f"[{link_text}]")
        
        # 본문 내용 추출 및 정리
        body_text = target.get_text()
        
        # HTML 엔티티 처리
        body_text = html_module.unescape(body_text)
        
        # 불필요한 공백/개행 제거
        body_text = re.sub(r'\n\s*\n', '\n\n', body_text)  # 여러 줄 공백 정리
        body_text = re.sub(r'\s{2,}', ' ', body_text)      # 연속된 공백 정리
        
        # CSS/스타일 관련 텍스트 제거
        body_text = re.sub(r'[.#]?[a-zA-Z0-9_-]+\s*\{[^}]*\}', '', body_text)
        body_text = re.sub(r'style=.*?["\']', '', body_text)
        body_text = re.sub(r'@media.*?\{.*?\}', '', body_text, flags=re.DOTALL)
        
        # 내용 정리 - 줄 단위로 처리
        clean_lines = []
        for line in body_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # CSS 선택자나 웹 코드로 보이는 줄 제거
            if re.match(r'^[.#]?[a-zA-Z0-9_-]+\s*\{', line) or ('{' in line and '}' in line):
                continue
                
            # 중요한 정보가 있는 줄만 유지
            if len(line) > 3 and not line.startswith(('.', '#', '{')):
                clean_lines.append(line)
                
        # 정리된 텍스트 구성
        body_text = '\n'.join(clean_lines)
        
        # 전체 텍스트 만들기
        full_message = header + body_text
        
        # 너무 길면 여러 메시지로 분할 (텔레그램 메시지 최대 길이: 약 4096자)
        MAX_LENGTH = 3000  # 여유있게 설정
        
        # 메시지 청크로 분할
        messages = []
        remaining_text = full_message
        
        # 첫 번째 메시지에는 헤더 포함
        first_chunk = remaining_text[:MAX_LENGTH]
        messages.append(first_chunk)
        remaining_text = remaining_text[MAX_LENGTH:]
        
        # 나머지 텍스트가 있으면 계속 분할
        while remaining_text:
            chunk = remaining_text[:MAX_LENGTH]
            remaining_text = remaining_text[MAX_LENGTH:]
            messages.append(chunk)
            
        # 메시지 전송
        success = True
        for i, message in enumerate(messages):
            # 첫 번째 메시지가 아니라면, 계속 표시
            if i > 0:
                message = "(계속) " + message
                
            result = await send_message(message)
            if not result:
                success = False
                logger.error(f"메시지 {i+1}/{len(messages)} 전송 실패")
        
        # 링크가 있으면 별도 메시지로 전송
        if links:
            links_text = f"🔗 <b>{ticker} 뉴스 링크</b>\n\n"
            for i, link in enumerate(links):  # 모든 링크 표시
                links_text += f"{i+1}. {link}\n\n"
                
            # 링크 메시지가 너무 길면 분할
            if len(links_text) > 4000:
                # 최대 5개만 포함
                links_text = f"🔗 <b>{ticker} 뉴스 링크</b> (최신 5개)\n\n"
                for i, link in enumerate(links[:5]):
                    links_text += f"{i+1}. {link}\n\n"
            
            await send_message(links_text)
                
        return success
        
    except Exception as e:
        logger.error(f"HTML 내용 전송 실패: {e}")
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
    Create stock/ETF chart image
    
    Args:
        ticker (str): Ticker symbol
        data (dict): Chart data
        
    Returns:
        bytes: Image bytes data
    """
    try:
        # Prepare data
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in data.get('dates', [])]
        prices = data.get('prices', [])
        ma50 = data.get('ma50', [])
        ma200 = data.get('ma200', [])
        ma200_plus10 = data.get('ma200_plus10', [])
        
        # Set figure and background
        plt.figure(figsize=(10, 6), facecolor='black')
        plt.style.use('dark_background')
        
        # Set axes background
        ax = plt.gca()
        ax.set_facecolor('black')
        
        # Price graph
        plt.plot(dates, prices, color='#00BFFF', linewidth=2, label='Price')
        
        # Moving averages
        valid_ma50 = [(d, p) for d, p in zip(dates, ma50) if p is not None]
        if valid_ma50:
            ma50_dates, ma50_values = zip(*valid_ma50)
            plt.plot(ma50_dates, ma50_values, color='#FFD700', linewidth=1.5, label='50-day MA')
        
        valid_ma200 = [(d, p) for d, p in zip(dates, ma200) if p is not None]
        if valid_ma200:
            ma200_dates, ma200_values = zip(*valid_ma200)
            plt.plot(ma200_dates, ma200_values, color='#FF4500', linewidth=1.5, label='200-day MA')
            
        # Add 200-day MA +10% line
        valid_ma200_plus10 = [(d, p) for d, p in zip(dates, ma200_plus10) if p is not None]
        if valid_ma200_plus10:
            ma200_plus10_dates, ma200_plus10_values = zip(*valid_ma200_plus10)
            plt.plot(ma200_plus10_dates, ma200_plus10_values, color='#FF69B4', linewidth=1.5, linestyle='--', label='200-day MA +10%')
        
        # Graph style settings
        plt.grid(True, alpha=0.3)
        plt.title(f"{ticker} Price Chart (1Y)", fontsize=16, pad=10)
        plt.ylabel("Price (USD)", fontsize=12)
        
        # X축 날짜 형식
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45, fontsize=10, color='white')
        plt.yticks(fontsize=10, color='white')
        
        # 축 가시성 향상
        plt.gca().spines['left'].set_visible(True)
        plt.gca().spines['left'].set_color('gray')
        plt.gca().spines['bottom'].set_visible(True)
        plt.gca().spines['bottom'].set_color('gray')
        
        # 눈금 표시 확실하게
        plt.gca().tick_params(axis='x', colors='gray', length=5)
        plt.gca().tick_params(axis='y', colors='gray', length=5)
        
        # 범례 가시성 향상
        plt.legend(frameon=True, framealpha=0.8, fontsize=10)
        
        # 차트 주변 여백 확보
        plt.tight_layout(pad=2.0)
        
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


def create_text_image(ticker, content):
    """
    텍스트 내용을 이미지로 변환
    
    Args:
        ticker (str): 티커 심볼
        content (str): 표시할 텍스트 내용
        
    Returns:
        bytes: 이미지 바이트 데이터
    """
    try:
        # BeautifulSoup으로 HTML 처리 및 링크 추출
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # 브리핑 본문의 링크만 추출 (주요 내용 영역)
        links = []
        
        # 주로 브리핑 본문이 포함된 영역 찾기 - 'content', 'briefing', 'article' 등의 클래스 이름 시도
        content_section = None
        for class_name in ['etf-content', 'etf-briefing', 'daily-briefing', 'article', 'content']:
            found = soup.find(class_=lambda x: x and class_name in str(x).lower())
            if found:
                content_section = found
                break
        
        # 본문 영역을 찾지 못했다면 전체 문서에서 링크 찾기
        target = content_section if content_section else soup
        
        # 링크 추출 및 처리
        for a in target.find_all('a', href=True):
            href = a['href']
            # 상대 경로 링크는 건너뛰기
            if href.startswith('/') or href.startswith('#'):
                continue
                
            # 실제 URL만 포함 (javascript 링크 제외)
            if href.startswith('http'):
                link_text = a.get_text(strip=True) or href
                # 브리핑 원문 링크 정보 저장
                links.append(f"<a href='{href}'>{link_text}</a>")
                
                # 링크는 [원문 보기]로 대체 (텍스트에서는 제거)
                a.replace_with("[원문 보기]")
            
        # HTML에서 텍스트 추출
        cleaned_content = soup.get_text()
        
        # HTML entity 처리
        cleaned_content = html.unescape(cleaned_content)
        
        # 여러 줄 개행 정리
        cleaned_content = re.sub(r'\n\s*\n', '\n\n', cleaned_content)
        
        # 사용자 예시에 맞는 이미지 생성
        # 이미지 설정
        width = 1000
        line_count = len(cleaned_content.split('\n'))
        height = max(500, 100 + line_count * 25)  # 기본 높이 500px, 줄 수에 따라 증가
        
        # matplotlib으로 이미지 생성 (한글 폰트 문제 우회)
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        # 도표 크기 및 배경 설정
        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
        
        # 배경색 설정 - 진한 남색 (RGB 값을 0-1 범위로 변환)
        background_color = (20/255, 24/255, 40/255)  # 어두운 남색
        fig.patch.set_facecolor(background_color)
        ax.set_facecolor(background_color)
        
        # 테두리 색상
        border_color = (100/255, 140/255, 240/255)  # 테두리 색상
        header_color = (66/255, 133/255, 244/255)  # 파란색
        text_color = (240/255, 240/255, 245/255)  # 흰색에 가까운 색
        
        # 축 제거
        ax.axis('off')
        
        # 테두리 추가
        rect = patches.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor=border_color, facecolor='none', 
                               transform=ax.transAxes)
        ax.add_patch(rect)
        
        # 티커 심볼 (좌상단)
        ax.text(0.03, 0.95, ticker, fontsize=20, color=header_color, weight='bold', 
               transform=ax.transAxes)
        
        # 날짜 (우상단)
        current_date = datetime.now().strftime("%Y-%m-%d")
        date_text = f"데일리 브리핑 ({current_date})"
        ax.text(0.97, 0.95, date_text, fontsize=14, color=header_color, 
               horizontalalignment='right', transform=ax.transAxes)
        
        # 구분선
        ax.axhline(y=0.92, xmin=0.03, xmax=0.97, color=header_color, linewidth=1)
        
        # 본문 내용 - 줄바꿈 처리된 텍스트
        # 내용이 깨지지 않도록 텍스트 대신 영문/숫자 요약 표시
        filtered_content = []
        for line in cleaned_content.split('\n'):
            # 한글이 포함된 줄은 기본 메시지로 대체
            if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in line):
                # 영문과 숫자 및 기본 구두점만 유지
                english_only = ''.join([c if ord(c) < 128 else ' ' for c in line])
                filtered_content.append(english_only)
            else:
                filtered_content.append(line)
                
        display_text = '\n'.join(filtered_content)
        
        # 본문 텍스트 표시
        ax.text(0.03, 0.85, display_text, fontsize=12, color=text_color, 
               verticalalignment='top', linespacing=1.5, transform=ax.transAxes)
        
        # 이미지를 바이트로 변환
        img_buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img_buf, format='png', dpi=100)
        img_buf.seek(0)
        plt.close()
        
        # 로깅 추가
        logger.info(f"차트 이미지 생성 완료: 크기 {width}x{height}")
        
        return {
            'image': img_buf.getvalue(),
            'links': links
        }
        
    except Exception as e:
        logger.error(f"텍스트 이미지 생성 실패: {e}")
        return None


async def send_briefing_as_image(ticker, html_content):
    """
    브리핑 내용을 이미지로 변환하여 텔레그램으로 전송
    
    Args:
        ticker (str): 티커 심볼
        html_content (str): HTML 내용
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 이미지 생성
        result = create_text_image(ticker, html_content)
        
        if not result:
            logger.error(f"브리핑 이미지 생성 실패: {ticker}")
            # 일반 텍스트 방식으로 폴백
            return await send_html_content(ticker, html_content)
            
        image_bytes = result['image']
        links = result.get('links', [])
        
        # 이미지 캡션 (현재 날짜 포함)
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        caption = f"{ticker} 데일리 브리핑 ({current_date})"
        
        # 이미지 전송
        image_success = await send_photo(image_bytes, caption=caption)
        
        # 링크가 있으면 별도 메시지로 전송
        if links and image_success:
            links_text = f"🔗 <b>{ticker} 뉴스 링크</b>\n\n"
            for i, link in enumerate(links):  # 모든 링크 표시
                links_text += f"{i+1}. {link}\n\n"
                
            # 링크 메시지가 너무 길면 분할
            if len(links_text) > 4000:
                # 최대 5개만 포함
                links_text = f"🔗 <b>{ticker} 뉴스 링크</b> (최신 5개)\n\n"
                for i, link in enumerate(links[:5]):
                    links_text += f"{i+1}. {link}\n\n"
            
            await send_message(links_text)
            
        return image_success
        
    except Exception as e:
        logger.error(f"브리핑 이미지 전송 실패: {e}")
        # 에러 발생 시 기존 텍스트 방식으로 폴백
        return await send_html_content(ticker, html_content)


# 직접 실행 시 테스트 수행
if __name__ == "__main__":
    asyncio.run(test_telegram())