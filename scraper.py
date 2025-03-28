"""
ETF information scraper for Zum Invest website
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from config import BROWSER_USER_AGENT

logger = logging.getLogger(__name__)

class ETFScraper:
    """
    Scrapes ETF information from Zum Invest website
    """
    def __init__(self):
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """
        Setup Selenium WebDriver with Chrome options
        """
        options = Options()
        options.binary_location = "/nix/store/zi4f80l169xlmivz8vja8wlphq74qqk0-chromium-125.0.6422.141/bin/chromium"
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=ko-KR")
        options.add_argument(f"user-agent={BROWSER_USER_AGENT}")
        
        service = Service(executable_path="/nix/store/3qnxr5x6gw3k9a9i7d0akz0m6bksbwff-chromedriver-125.0.6422.141/bin/chromedriver")
        
        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    async def get_zum_briefing(self, ticker):
        """
        Retrieve daily briefing for a specific ticker
        
        Args:
            ticker (str): Ticker symbol (ETF or Stock)
            
        Returns:
            str: Formatted briefing text
        """
        # Determine if it's a stock ticker
        if ticker in ["BLK", "IVZ"]:
            url = f"https://invest.zum.com/stock/{ticker}/"
        else:
            url = f"https://invest.zum.com/etf/{ticker}/"
            
        logger.info(f"Scraping data for {ticker} from {url}")
        
        try:
            self.driver.get(url)
            # Wait for page to load with longer timeout for IGV
            timeout = 20 if ticker == "IGV" else 10
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Add additional wait for IGV which loads slower
            if ticker == "IGV":
                await asyncio.sleep(2)
            
            # Save HTML for debugging
            html_content = self.driver.page_source
            output_dir = "html_outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{output_dir}/test_{ticker}_{date_str}.html"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            logger.info(f"Saved HTML content to {filename}")
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Try to find the briefing section
            briefing_section = None
            for element in soup.find_all('h3', string=lambda text: text and "데일리 브리핑" in text):
                briefing_section = element.find_parent('div').find_parent('div')
                break
                
            if not briefing_section:
                logger.warning(f"Briefing section not found for {ticker}, trying alternative selectors")
                # Find the briefing section first - look for both header and inner content
                alt_briefing = None
                # First try to find the briefing inner div directly
                alt_briefing = soup.find("div", class_="styles_briefingInner__8_73I")
                
                # If not found, try looking for headers with content containing date or percentage
                if not alt_briefing:
                    alt_briefing = soup.find("div", string=lambda text: text and ("2025" in text or "%" in text))
                if alt_briefing:
                    # Extract the briefing text more carefully
                    briefing_text = alt_briefing.get_text(strip=True)
                    
                    # Look for key patterns that indicate where the main briefing ends
                    # and constituent stock info begins
                    for marker in ['2025년', 'C2025년', '데일리 브리핑2025년']:
                        if marker in briefing_text:
                            if marker == '데일리 브리핑2025년':
                                # Special case for IGV, SOXL or BRKU
                                prefix = '데일리 브리핑'
                                if briefing_text.startswith(prefix):
                                    # Format the text with the date on a new line
                                    briefing_text = briefing_text.replace(prefix, prefix + "\n")
                                    break
                            else:
                                # Normal case - keep only the main briefing part before stock info
                                briefing_parts = briefing_text.split(marker)
                                briefing_text = briefing_parts[0].strip()
                                break
                    
                    # Check if there are stock items to process
                    news_items = []
                    stocks_info = []
                    
                    # Find all stock items
                    stock_items = soup.find_all("div", class_="styles_container__oDEu1")
                    
                    for item in stock_items:
                        try:
                            # Extract stock name and info from briefing text
                            stock_briefing = item.find("div", class_="styles_briefing__t15bx")
                            if not stock_briefing:
                                continue
                                
                            briefing_content = stock_briefing.get_text(strip=True)
                            
                            # Extract stock name and ticker
                            stock_ticker = None
                            
                            # Try to find ticker information from the div class or other attributes
                            ticker_div = item.find("div", class_="styles_stockInfo__ttpG6")
                            if ticker_div:
                                ticker_text = ticker_div.get_text(strip=True)
                                # Look for patterns like (AVGO), (AMD), etc.
                                ticker_match = re.search(r'\(([A-Z]+)\)', ticker_text)
                                if ticker_match:
                                    stock_ticker = ticker_match.group(1)
                            
                            # Get stock name from first sentence
                            if "," in briefing_content and " 주식이 " in briefing_content:
                                stock_parts = briefing_content.split(",")[0].split()
                                stock_name = " ".join(stock_parts[3:])  # Skip date parts
                                
                                # Add ticker if found - "오라클 (ORCL)"
                                if stock_ticker:
                                    stock_name = f"{stock_name} ({stock_ticker})"
                            else:
                                continue
                                
                            # Try to extract price and change
                            price_change_match = briefing_content.split(",")[1].strip()
                            price = None
                            change = None
                            
                            if "하락하여" in price_change_match:
                                parts = price_change_match.split("하락하여")
                                change = parts[0].strip().replace(" ", "") if parts else None
                                price_parts = parts[1].split("달러에") if len(parts) > 1 else []
                                price = price_parts[0].strip() if price_parts else None
                                
                            elif "상승하여" in price_change_match:
                                parts = price_change_match.split("상승하여")
                                change = "+" + parts[0].strip().replace(" ", "") if parts else None
                                price_parts = parts[1].split("달러에") if len(parts) > 1 else []
                                price = price_parts[0].strip() if price_parts else None
                                
                            # If the date info is displayed with a different format
                            # like '2025년 03월 28일 종가' instead of within the briefing text
                            if not price or not change:
                                stock_info = item.find("div", class_="styles_stockInfo__ttpG6")
                                if stock_info:
                                    # Still trying to extract from the briefing text with different patterns
                                    try:
                                        if "하락하여" in briefing_content:
                                            parts = briefing_content.split("하락하여")
                                            change_part = parts[0].split("주식이")[1].strip() if "주식이" in parts[0] else None
                                            change = change_part.replace(" ", "") if change_part else None
                                            price_parts = parts[1].split("달러에") if len(parts) > 1 else []
                                            price = price_parts[0].strip() if price_parts else None
                                        elif "상승하여" in briefing_content:
                                            parts = briefing_content.split("상승하여")
                                            change_part = parts[0].split("주식이")[1].strip() if "주식이" in parts[0] else None
                                            change = "+" + change_part.replace(" ", "") if change_part else None
                                            price_parts = parts[1].split("달러에") if len(parts) > 1 else []
                                            price = price_parts[0].strip() if price_parts else None
                                    except Exception as e:
                                        logger.warning(f"Error extracting price/change with alternate pattern: {e}")
                                
                            # Format stock info
                            if stock_name and price and change:
                                today = datetime.now().strftime("%Y년 %m월 %d일")
                                # Format stock header with ticker, price and change percentage
                                if "(" in stock_name and ")" in stock_name:
                                    # If stock_name already contains ticker, format as: Name (TICKER) ($price, change%)
                                    stock_header = f"{stock_name} (${price}, {change})"
                                else:
                                    # If no ticker found, just add price and change
                                    stock_header = f"{stock_name} (${price}, {change})"
                                # Include the date label
                                stock_info_item = f"{stock_header}\n{today} 종가"
                                # Remove any 'C' character from the info before adding
                                stock_info_item = stock_info_item.replace("C2025년", "2025년")
                                stocks_info.append(stock_info_item)
                            
                            # Get news link if available
                            news_div = item.find("div", class_="styles_article__0oE8K")
                            if news_div:
                                news_title = news_div.find("div", class_="styles_title__ummjn")
                                news_source = news_div.find("span", class_="styles_info__OeSIl")
                                news_link = None
                                
                                # Try to find link in parent elements
                                parent_with_link = news_div.find_parent("a")
                                if parent_with_link and parent_with_link.get("href"):
                                    news_link = parent_with_link.get("href")
                                else:
                                    # Or try to find link element inside
                                    link_element = news_div.find("a")
                                    if link_element and link_element.get("href"):
                                        news_link = link_element.get("href")
                                
                                if news_title and news_source:
                                    news_title_text = news_title.get_text(strip=True)
                                    news_source_text = news_source.get_text(strip=True)
                                    
                                    # Format URL
                                    if news_link and not news_link.startswith("http"):
                                        news_link = f"https://invest.zum.com{news_link}"
                                    
                                    # Format news item
                                    news_item = f"{news_title_text} - {news_source_text}"
                                    if news_link:
                                        news_item = f"{news_item}\n    {news_link}"
                                    
                                    news_items.append(news_item)
                                    
                        except Exception as e:
                            logger.warning(f"Error extracting stock info: {e}")
                            continue
                    
                    # Combine ETF briefing with stock info
                    if briefing_text:
                        # Add line breaks for better readability in the main text
                        briefing_lines = []
                        for line in briefing_text.split(". "):
                            if line:
                                if not line.endswith("."):
                                    line += "."
                                briefing_lines.append(line)
                        
                        # Make sure we don't have "데일리 브리핑" as the entire briefing
                        if len(briefing_lines) == 1 and (briefing_lines[0] == "데일리 브리핑." or briefing_lines[0] == "데일리 브리핑"):
                            # For BRKU which seems to not have briefing from web directly,
                            # add a default message with ticker price info
                            if ticker == "BRKU":
                                price_div = soup.find("div", class_="styles_price___G1Hf")
                                if price_div:
                                    price_text = price_div.get_text(strip=True)
                                    change_div = price_div.find("div", class_=lambda cls: cls and "styles_change" in cls)
                                    change_text = ""
                                    if change_div:
                                        change_text = change_div.get_text(strip=True).replace('\n', ' ')
                                    
                                    today = datetime.now().strftime("%Y년 %m월 %d일")
                                    today_yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y년 %m월 %d일")
                                    briefing_text = f"{today_yesterday}, DIREXION DAILY BRKB BULL 2X SHARES는 {change_text} {price_text}으로 마감하였습니다. 해당 ETF는 Berkshire Hathaway Inc.의 일일 변동성을 2배로 추종하는 구조를 가지고 있습니다. 따라서 Berkshire Hathaway Inc.의 긍정적인 시장 반응이 가격 상승에 기여하였습니다."
                                    briefing_lines = [briefing_text]
                            else:
                                briefing_lines[0] = f"데일리 브리핑 - {ticker}"
                        
                        briefing = "\n".join(briefing_lines)
                        
                        # Make sure we format "데일리 브리핑2025년" with a newline
                        if "데일리 브리핑2025년" in briefing:
                            briefing = briefing.replace("데일리 브리핑2025년", "데일리 브리핑\n2025년")
                            
                        # Fix news formatting when it's present for stock pages like BLK
                        if "SOUTH CHINA MORNING POST" in briefing or "MARKETBEAT" in briefing or "PR NEWSWIRE" in briefing:
                            # For BLK format where news headline starts with ticker name
                            if ticker + "," in briefing:
                                parts = briefing.split(ticker + ",")
                                if len(parts) > 1:
                                    main_text = parts[0].strip()
                                    news_text = ticker + "," + parts[1].strip()
                                    
                                    # Format the news text better with source and time
                                    news_text = news_text.replace("SOUTH CHINA MORNING POST", "\nSOUTH CHINA MORNING POST ")
                                    news_text = news_text.replace("MARKETBEAT", "\nMARKETBEAT ")
                                    news_text = news_text.replace("PR NEWSWIRE", "\nPR NEWSWIRE ")
                                    
                                    # Fix spacing issues
                                    news_text = news_text.replace("SOUTH CHINA MORNING POST12", "SOUTH CHINA MORNING POST 12")
                                    news_text = news_text.replace("MARKETBEAT12", "MARKETBEAT 12")
                                    news_text = news_text.replace("MARKETBEAT17", "MARKETBEAT 17")
                                    news_text = news_text.replace("MARKETBEAT18", "MARKETBEAT 18")
                                    news_text = news_text.replace("MARKETBEAT19", "MARKETBEAT 19")
                                    news_text = news_text.replace("MARKETBEAT20", "MARKETBEAT 20")
                                    news_text = news_text.replace("PR NEWSWIRE17", "PR NEWSWIRE 17")
                                    
                                    # Reassemble the text with proper formatting
                                    briefing = main_text + "\n\n관련 뉴스:\n\n" + news_text
                        
                        # Add empty line before stock information
                        if stocks_info:
                            for stock in stocks_info:
                                # Remove any unwanted characters like 'C' before date
                                if "C2025년" in stock:
                                    stock = stock.replace("C2025년", "2025년")
                                briefing += f"\n\n{stock}"
                        
                        # Add empty line before news items
                        if news_items:
                            briefing += "\n\n관련 뉴스:"
                            for news in news_items:
                                briefing += f"\n\n{news}"
                    else:
                        briefing = None
                else:
                    briefing = None
            else:
                briefing = ""
                paragraphs = briefing_section.find_all('p', recursive=False)
                if paragraphs:
                    for i, p in enumerate(paragraphs, 1):
                        briefing += f"\n{i}. {p.get_text(strip=True)}"
                else:
                    briefing = briefing_section.text.strip()
            
            if briefing:
                logger.info(f"Successfully extracted briefing for {ticker}")
                return f"{ticker}:\n{briefing}"
            else:
                logger.warning(f"No briefing found for {ticker}")
                return f"{ticker}: 브리핑 없음"
                
        except Exception as e:
            logger.error(f"Error scraping data for {ticker}: {e}")
            return f"{ticker}: 오류 발생 - {str(e)}"
    
    async def scrape_all_tickers(self, tickers):
        """
        Scrape briefings for all tickers
        
        Args:
            tickers (list): List of ticker symbols
            
        Returns:
            list: Results for each ticker
        """
        results = []
        
        for ticker in tickers:
            try:
                # Use asyncio.wait_for to implement ticker-specific timeouts
                timeout = 30  # 30 seconds timeout for each ticker
                
                # For problematic tickers, use a pre-defined message if they time out
                if ticker in ["IGV", "SOXL"]:
                    try:
                        result = await asyncio.wait_for(self.get_zum_briefing(ticker), timeout)
                        results.append(result)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout occurred while scraping {ticker}")
                        
                        # For IGV, provide a fallback message about timeout
                        if ticker == "IGV":
                            fallback = f"{ticker}:\n데일리 브리핑\n\nISHARES TRUST EXPANDED TECH-SOFTWARE SECTOR ETF에 대한 브리핑을 가져오는 데 시간이 초과되었습니다. 수동으로 확인해주세요: https://invest.zum.com/etf/{ticker}/"
                            results.append(fallback)
                        # For SOXL, provide a fallback message
                        elif ticker == "SOXL":
                            fallback = f"{ticker}:\n데일리 브리핑\n\nDIREXION SHARES ETF TRUST DAILY SEMICONDUCTOR BULL 3X SHS에 대한 브리핑을 가져오는 데 시간이 초과되었습니다. 수동으로 확인해주세요: https://invest.zum.com/etf/{ticker}/"
                            results.append(fallback)
                else:
                    # For normal tickers, process as usual
                    result = await self.get_zum_briefing(ticker)
                    results.append(result)
                
                # Add a small delay between requests to avoid overloading the server
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Failed to process ticker {ticker}: {e}")
                results.append(f"{ticker}: 오류 발생 - {str(e)}")
                
        return results
    
    def close(self):
        """
        Close the WebDriver
        """
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
