"""
Configuration settings for ETF data scraper
"""

# List of tickers to track
TICKERS = ["IGV", "SOXL", "BRKU", "BLK", "IVZ"]

# Test ticker subset (only stable ones)
TEST_TICKERS = ["BLK"]

# Schedule settings (24-hour format)
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_FILE = "etf_scraper.log"

# Browser settings
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
