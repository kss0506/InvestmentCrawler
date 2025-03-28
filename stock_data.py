"""
Stock/ETF data retrieval functions for charts and metrics
"""
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("stock_data.log")
    ]
)
logger = logging.getLogger(__name__)


def get_stock_data(ticker, period="1y"):
    """
    Get historical stock data for a ticker

    Args:
        ticker (str): Stock ticker symbol
        period (str): Time period, default: 1y (1 year)

    Returns:
        dict: Stock data in chart-friendly format with moving averages
        None: If error occurs
    """
    try:
        # Get stock data
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)

        if history.empty:
            logger.error(f"Failed to get data for {ticker}")
            return None

        # Calculate moving averages
        history['MA50'] = history['Close'].rolling(window=50).mean()
        history['MA200'] = history['Close'].rolling(window=200).mean()
        history['MA200_Plus10'] = history['MA200'] * 1.1

        # Format data for the chart - NaN 값을 None으로 변환하여 JSON 직렬화 가능하게 만듦
        dates = history.index.strftime('%Y-%m-%d').tolist()
        prices = [float(x) if not pd.isna(x) else None for x in history['Close'].tolist()]
        ma50 = [float(x) if not pd.isna(x) else None for x in history['MA50'].tolist()]
        ma200 = [float(x) if not pd.isna(x) else None for x in history['MA200'].tolist()]
        ma200_plus10 = [float(x) if not pd.isna(x) else None for x in history['MA200_Plus10'].tolist()]

        # Get current values - NaN 값 처리
        current_price = float(prices[-1]) if prices[-1] is not None else None
        current_ma50 = float(ma50[-1]) if ma50[-1] is not None else None
        current_ma200 = float(ma200[-1]) if ma200[-1] is not None else None
        current_ma200_plus10 = float(ma200_plus10[-1]) if ma200_plus10[-1] is not None else None

        # Check if price is above MA200 and MA200+10% (None 값 처리)
        is_above_ma200 = current_price > current_ma200 if current_price is not None and current_ma200 is not None else False
        is_above_ma200_plus10 = current_price > current_ma200_plus10 if current_price is not None and current_ma200_plus10 is not None else False

        return {
            'dates': dates,
            'prices': prices,
            'ma50': ma50,
            'ma200': ma200,
            'ma200_plus10': ma200_plus10,
            'current_price': current_price,
            'current_ma50': current_ma50,  # 이미 None으로 변환됨
            'current_ma200': current_ma200,  # 이미 None으로 변환됨
            'current_ma200_plus10': current_ma200_plus10,  # 이미 None으로 변환됨
            'is_above_ma200': is_above_ma200,
            'is_above_ma200_plus10': is_above_ma200_plus10
        }
    except Exception as e:
        logger.error(f"Error getting stock data for {ticker}: {e}")
        return None


def get_stock_info(ticker):
    """
    Get basic info about a stock/ETF

    Args:
        ticker (str): Stock ticker symbol

    Returns:
        dict: Basic info about the stock/ETF
        None: If error occurs
    """
    try:
        # Get stock info
        stock = yf.Ticker(ticker)
        info = stock.info

        # Return basic info
        return {
            'name': info.get('shortName', ticker),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'dividend_yield': info.get('dividendYield', 'N/A'),
            'beta': info.get('beta', 'N/A'),
            'description': info.get('longBusinessSummary', 'N/A')
        }
    except Exception as e:
        logger.error(f"Error getting stock info for {ticker}: {e}")
        return None