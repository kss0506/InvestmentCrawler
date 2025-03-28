"""
ETF information scraper for Zum Invest website
"""
import asyncio
import logging
import os
from datetime import datetime

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
        Retrieve daily briefing for a specific ETF ticker
        
        Args:
            ticker (str): ETF ticker symbol
            
        Returns:
            str: Formatted briefing text
        """
        url = f"https://invest.zum.com/etf/{ticker}/"
        logger.info(f"Scraping data for {ticker} from {url}")
        
        try:
            self.driver.get(url)
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
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
                alt_briefing = soup.find("div", class_="styles_briefingInner__8_73I") or \
                               soup.find("div", string=lambda text: text and ("2025" in text or "%" in text))
                if alt_briefing:
                    briefing_text = alt_briefing.get_text(strip=True).split('C2025년')[0].strip()
                    
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
                            
                            # Get stock name from first sentence
                            if "," in briefing_content and " 주식이 " in briefing_content:
                                stock_parts = briefing_content.split(",")[0].split()
                                stock_name = " ".join(stock_parts[3:])  # Skip date parts
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
                                stocks_info.append(f"{stock_name} (${price}, {change})")
                            
                            # Get news link if available
                            news_div = item.find("div", class_="styles_article__0oE8K")
                            if news_div:
                                news_title = news_div.find("div", class_="styles_title__ummjn")
                                news_source = news_div.find("span", class_="styles_info__OeSIl")
                                
                                if news_title and news_source:
                                    news_title_text = news_title.get_text(strip=True)
                                    news_source_text = news_source.get_text(strip=True)
                                    news_items.append(f"[{news_title_text}] - {news_source_text}")
                                    
                        except Exception as e:
                            logger.warning(f"Error extracting stock info: {e}")
                            continue
                    
                    # Combine ETF briefing with stock info
                    if briefing_text:
                        briefing = briefing_text
                        if stocks_info:
                            briefing += "\n\n주요 구성종목:"
                            for idx, stock in enumerate(stocks_info, 1):
                                briefing += f"\n{idx}. {stock}"
                        
                        if news_items:
                            briefing += "\n\n관련 뉴스:"
                            for idx, news in enumerate(news_items, 1):
                                briefing += f"\n{idx}. {news}"
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
