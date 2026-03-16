[Insert System Architecture Diagram Here]

Figure 1: System Architecture Overview

┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │   Dashboard     │  │   Trading       │  │   Analytics     │    │
│  │   Component     │  │   Component     │  │   Component     │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│        │                       │                      │           │
│        │                       │                      │           │
│        └───────────────────────┼──────────────────────┘           │
│                                │                                  │
└────────────────────────────────┼──────────────────────────────────┘
                                 │
┌────────────────────────────────┼──────────────────────────────────┐
│                        APPLICATION LAYER                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │"""Main pipeline script for Phase 2.

Flow:
1) Fetch latest news headlines for a ticker
2) Store article data
3) Run sentiment analysis on each headline and store results
4) Fetch recent stock prices and store them
"""

import argparse

from config import Config
from database import (
    get_article_id_by_url,
    init_db,
    insert_articles,
    insert_prices,
    insert_sentiment,
)
from news_fetcher import fetch_news_for_ticker
from price_fetcher import fetch_last_30_days_prices
from sentiment_analyzer import SentimentAnalyzer


def run_pipeline(ticker: str) -> None:
    """Run the full fetch-analyze-store pipeline for one stock ticker."""
    ticker = ticker.upper().strip()

    print(f"\n{'='*40}")
    print(f"PROCESSING TICKER: {ticker}")
    print(f"{'='*40}")

    init_db()

    print(f"[{ticker}] Fetching news headlines...")
    articles = fetch_news_for_ticker(ticker)
    inserted_articles = insert_articles(ticker, articles)

    print(f"[{ticker}] Running sentiment analysis on headlines...")
    analyzer = SentimentAnalyzer()
    inserted_sentiments = 0

    for article in articles:
        article_id = get_article_id_by_url(article.get("url"))
        if not article_id:
            continue

        result = analyzer.analyze_headline(article.get("title", ""))
        inserted_sentiments += insert_sentiment(
            article_id=article_id,
            model_name=result["model"],
            label=result["label"],
            score=result["score"],
        )

    print(f"[{ticker}] Fetching historical prices...")
    prices = fetch_last_30_days_prices(ticker)
    inserted_prices = insert_prices(ticker, prices)

    print(f"\n[{ticker}] Pipeline completed.")
    print(f"Articles fetched:   {len(articles)} | inserted: {inserted_articles}")
    print(f"Sentiments stored:  {inserted_sentiments}")
    print(f"Prices fetched:     {len(prices)} | inserted: {inserted_prices}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Stock Dashboard Phase 2 Pipeline")
    parser.add_argument(
        "ticker",
        nargs="?",
        default="ALL",
        help="Stock ticker symbol or 'ALL' for batch processing (default: ALL)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    if args.ticker.upper() == "ALL":
        print(f"Starting batch process for: {Config.DEFAULT_TICKERS}")
        for t in Config.DEFAULT_TICKERS:
            try:
                run_pipeline(t)
            except Exception as e:
                print(f"Error processing {t}: {e}")
    else:
        run_pipeline(args.ticker)

