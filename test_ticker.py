import asyncio
import sys
import re
from main import setup_logging
from scraper import ETFScraper

async def test_ticker(ticker):
    logger = setup_logging()
    scraper = ETFScraper()
    try:
        result = await scraper.get_zum_briefing(ticker)

        # Implement custom formatting here for output
        if "데일리 브리핑2025년" in result:
            # Remove extra "데일리 브리핑" in the content
            result = result.replace("데일리 브리핑2025년", "2025년")
            result = result.replace("데일리 브리핑\n", "")

        if "C2025년" in result:
            result = result.replace("C2025년", "\n\n2025년")

        # Format stock headers with clean dividers and simplified price format
        for stock, ticker in [("팔로 알토 네트웍스", "PANW"), ("팔란티어 테크놀로지스", "PLTR"), ("오라클", "ORCL")]:
            pattern = f"{stock} \\({ticker}\\)\\$(\\d+\\.\\d+)-([\\d\\.]+)"
            replacement = f"\n\n━━━ {stock} ({ticker}) ━━━\n$\\1 (-\\2%)"
            result = re.sub(pattern, replacement, result)

        # Format news sources and times
        for source in ["SOUTH CHINA MORNING POST", "MARKETBEAT", "PR NEWSWIRE"]:
            if source in result:
                # Add newline before news source
                result = result.replace(source, f"\n{source} ")

                # Fix spacing with time
                for hour in range(12, 25):
                    result = result.replace(f"{source}{hour}", f"{source} {hour}")

        # Special formatting for SOXL ticker
        if "브로드컴 (AVGO)" in result:
            result = result.replace("브로드컴 (AVGO)", "\n\n브로드컴 (AVGO)")

        # Format news sections better
        if "관련 뉴스:" not in result:
            # For IGV ticker with multiple news sections
            if "팔로 알토 네트웍스" in result or "팔란티어 테크놀로지스" in result or "오라클" in result:
                news_start = result.find("팔로 알토 네트웍스")
                if news_start == -1:
                    news_start = result.find("팔란티어 테크놀로지스")
                if news_start == -1:
                    news_start = result.find("오라클")

                if news_start != -1:
                    # Split the text and add news section header
                    main_content = result[:news_start].strip()
                    news_content = result[news_start:].strip()
                    result = main_content + "\n\n관련 뉴스:\n\n" + news_content

            # Add spaces between ticker symbol, price, and change percentage

        # For BLK specific format - must be after the general formatting
        if "SOUTH CHINA MORNING POST" in result and "블랙록," in result:
            # Split text at the news headline
            parts = result.split("블랙록,")
            if len(parts) > 1:
                main_text = parts[0].strip()
                news_text = "블랙록," + parts[1].strip()

                # Reassemble the text with proper formatting
                result = main_text + "\n\n관련 뉴스:\n\n" + news_text

        print("\n" + "="*50)
        print(result)
        print("="*50)
    finally:
        scraper.close()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BLK"
    asyncio.run(test_ticker(ticker))