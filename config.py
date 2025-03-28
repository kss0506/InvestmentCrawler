"""
Configuration settings for ETF data scraper
"""

# List of ETF tickers to track
TICKERS = ["IYY", "SPY", "QQQ", "VTI", "VOO", "IGV"]

# Schedule settings (24-hour format)
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_FILE = "etf_scraper.log"

# Browser settings
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
