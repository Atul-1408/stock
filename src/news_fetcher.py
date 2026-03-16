"""News fetching module using NewsAPI."""

from typing import Dict, List

import requests

from config import Config


def fetch_news_for_ticker(ticker: str) -> List[Dict]:
    """Fetch top headlines for a stock ticker from NewsAPI.

    Returns a list of simplified article dictionaries.
    """
    if not Config.NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY is missing. Add it to your .env file.")

    endpoint = "https://newsapi.org/v2/everything"

    # Use company name if mapped, otherwise use ticker
    search_query = Config.TICKER_NAME_MAP.get(ticker, ticker)

    params = {
        "q": search_query,
        "language": Config.NEWS_LANGUAGE,
        "sortBy": "publishedAt",
        "pageSize": Config.NEWS_PAGE_SIZE,
        "apiKey": Config.NEWS_API_KEY,
    }

    response = requests.get(endpoint, params=params, timeout=20)
    response.raise_for_status()

    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(f"NewsAPI error: {payload}")

    simplified_articles = []
    for article in payload.get("articles", []):
        simplified_articles.append(
            {
                "title": article.get("title"),
                "description": article.get("description"),
                "url": article.get("url"),
                "source": (article.get("source") or {}).get("name"),
                "published_at": article.get("publishedAt"),
            }
        )

    return simplified_articles
