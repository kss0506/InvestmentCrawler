"""
Flask web application for ETF Daily Briefing Scraper
"""
import os
import logging
import io
import base64
from datetime import datetime
import glob
import json

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response

# Import stock data module
from stock_data import get_stock_data, get_stock_info
from telegram_sender import create_stock_chart

# Setup Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-for-etf-scraper")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# ETF and Stock information
TICKERS = {
    "ETFs": {
        "IGV": "iShares Expanded Tech-Software Sector ETF",
        "SOXL": "Direxion Daily Semiconductor Bull 3X Shares",
        "BRKU": "Direxion Semiconductor Bull 2X Shares",
    },
    "Stocks": {
        "BLK": "BlackRock, Inc.",
        "IVZ": "Invesco Ltd.",
    }
}


def get_available_dates():
    """
    Get all available dates from saved HTML files
    
    Returns:
        list: List of dates in YYYYMMDD format
    """
    dates = set()
    html_files = glob.glob("html_outputs/test_*_*.html")
    
    for file_path in html_files:
        # Extract date from filename (test_TICKER_YYYYMMDD.html)
        try:
            filename = os.path.basename(file_path)
            date_str = filename.split("_")[-1].replace(".html", "")
            dates.add(date_str)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    return sorted(list(dates), reverse=True)


def get_tickers_for_date(date_str):
    """
    Get all tickers available for a specific date
    
    Args:
        date_str (str): Date in YYYYMMDD format
        
    Returns:
        dict: Dictionary of ticker types with lists of available tickers
    """
    available_tickers = {
        "ETFs": [],
        "Stocks": []
    }
    
    for ticker_type, tickers in TICKERS.items():
        for ticker in tickers:
            file_path = f"html_outputs/test_{ticker}_{date_str}.html"
            if os.path.exists(file_path):
                available_tickers[ticker_type].append(ticker)
    
    return available_tickers


def format_date(date_str):
    """
    Format date string from YYYYMMDD to YYYY년 MM월 DD일
    
    Args:
        date_str (str): Date in YYYYMMDD format
        
    Returns:
        str: Formatted date
    """
    try:
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}년 {month}월 {day}일"
    except:
        return date_str


def get_html_content(ticker, date_str):
    """
    Get the HTML content for a specific ticker and date
    
    Args:
        ticker (str): Ticker symbol
        date_str (str): Date in YYYYMMDD format
        
    Returns:
        str: HTML content or error message
    """
    file_path = f"html_outputs/test_{ticker}_{date_str}.html"
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"<p>Error reading HTML content: {str(e)}</p>"
    else:
        return f"<p>No data available for {ticker} on {format_date(date_str)}</p>"


@app.route('/')
def index():
    """Homepage - show available dates"""
    dates = get_available_dates()
    return render_template('index.html', dates=dates, format_date=format_date)


@app.route('/date/<date_str>')
def date_view(date_str):
    """Show tickers available for a specific date"""
    available_tickers = get_tickers_for_date(date_str)
    return render_template(
        'date.html', 
        date_str=date_str, 
        format_date=format_date,
        available_tickers=available_tickers,
        ticker_descriptions=TICKERS
    )


@app.route('/ticker/<ticker>/<date_str>')
def ticker_view(ticker, date_str):
    """Show HTML content for a specific ticker and date"""
    html_content = get_html_content(ticker, date_str)
    
    # Determine ticker type (ETF or Stock)
    ticker_type = None
    ticker_description = None
    for t_type, tickers in TICKERS.items():
        if ticker in tickers:
            ticker_type = t_type
            ticker_description = tickers[ticker]
            break
    
    return render_template(
        'ticker.html',
        ticker=ticker,
        date_str=date_str,
        format_date=format_date,
        html_content=html_content,
        ticker_type=ticker_type,
        ticker_description=ticker_description
    )


@app.route('/api/chart/<ticker>')
def chart_data(ticker):
    """
    API endpoint to get chart data for a ticker
    
    Args:
        ticker (str): Ticker symbol
        
    Returns:
        json: Chart data in JSON format
    """
    period = request.args.get('period', '1y')
    data = get_stock_data(ticker, period=period)
    
    if data:
        return jsonify({
            'success': True,
            'ticker': ticker,
            'data': data
        })
    else:
        return jsonify({
            'success': False,
            'ticker': ticker,
            'error': f"Failed to get data for {ticker}"
        }), 404


@app.route('/chart/<ticker>')
def chart_view(ticker):
    """
    View chart for a specific ticker
    
    Args:
        ticker (str): Ticker symbol
        
    Returns:
        html: Chart page
    """
    period = request.args.get('period', '1y')
    
    # Determine ticker type (ETF or Stock)
    ticker_type = None
    ticker_description = None
    for t_type, tickers in TICKERS.items():
        if ticker in tickers:
            ticker_type = t_type
            ticker_description = tickers[ticker]
            break
    
    return render_template(
        'chart.html',
        ticker=ticker,
        period=period,
        ticker_type=ticker_type,
        ticker_description=ticker_description
    )


@app.route('/chart-image/<ticker>')
def chart_image(ticker):
    """
    Generate and serve a chart image for a ticker
    
    Args:
        ticker (str): Ticker symbol
        
    Returns:
        Response: PNG image
    """
    period = request.args.get('period', '1y')
    data = get_stock_data(ticker, period=period)
    
    if not data:
        return "Chart data not available", 404
        
    # 차트 이미지 생성
    chart_bytes = create_stock_chart(ticker, data)
    
    if not chart_bytes:
        return "Chart generation failed", 500
        
    # PNG 이미지로 응답
    return Response(chart_bytes, mimetype='image/png')


@app.route('/chart-data-image/<ticker>')
def chart_data_image(ticker):
    """
    API endpoint to get chart data and base64 encoded image
    
    Args:
        ticker (str): Ticker symbol
        
    Returns:
        json: Chart data and base64 encoded image
    """
    period = request.args.get('period', '1y')
    data = get_stock_data(ticker, period=period)
    
    if not data:
        return jsonify({
            'success': False,
            'ticker': ticker,
            'error': f"Failed to get data for {ticker}"
        }), 404
    
    # 차트 이미지 생성
    chart_bytes = create_stock_chart(ticker, data)
    
    if not chart_bytes:
        return jsonify({
            'success': False,
            'ticker': ticker,
            'error': "Chart generation failed"
        }), 500
    
    # Base64로 인코딩
    encoded_image = base64.b64encode(chart_bytes).decode('utf-8')
    
    return jsonify({
        'success': True,
        'ticker': ticker,
        'data': data,
        'chart_image': encoded_image
    })


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)