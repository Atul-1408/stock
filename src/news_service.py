"""News service for normalizing, validating, deduplicating, and analyzing news articles.

Provides:
- URL canonicalization and title normalization
- Article deduplication
- Sentiment caching to avoid reprocessing unchanged articles
- Robust multi-provider fallback (yfinance -> NewsAPI -> Finnhub -> Database cache)
- Processing status tracking ('analyzed', 'cached', 'fallback')
"""

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
import yfinance as yf

from config import Config
import database
from sentiment_service import get_analyzer


def canonicalize_url(raw_url: Optional[str]) -> str:
    """Strip marketing and tracking query parameters from URLs for canonical matching."""
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url.strip())
        if not parsed.scheme or not parsed.netloc:
            return raw_url.strip()

        tracking_keys = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "ref", "fbclid", "gclid", "guccounter", "guce_referrer", "guce_referrer_sig",
        }
        filtered_queries = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in tracking_keys
        ]
        new_query = urlencode(filtered_queries)
        return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.params, new_query, ""))
    except Exception:
        return raw_url.strip()


def normalize_title(title: Optional[str]) -> str:
    """Normalize headline text: strip excess whitespace and HTML entities."""
    if not title:
        return ""
    clean = re.sub(r"<[^>]+>", "", title)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def compute_article_hash(title: str, url: str = "") -> str:
    """Generate a stable content hash based on normalized title text to deduplicate syndicated headlines."""
    norm_text = re.sub(r"[^a-z0-9]", "", title.lower())
    return hashlib.sha256(norm_text.encode("utf-8")).hexdigest()[:16]


def parse_publication_time(raw_time) -> str:
    """Convert various publication timestamp representations into a standardized UTC ISO string."""
    if not raw_time:
        return datetime.now(timezone.utc).isoformat()

    # Case 1: Unix epoch timestamp in seconds or milliseconds
    if isinstance(raw_time, (int, float)):
        try:
            # If greater than 1e11, it is likely in milliseconds
            seconds = raw_time / 1000.0 if raw_time > 1e11 else float(raw_time)
            return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    # Case 2: String date/timestamp
    if isinstance(raw_time, str):
        raw_str = raw_time.strip()
        # Already ISO format
        if "T" in raw_str:
            try:
                # Replace trailing 'Z' if needed or parse ISO
                dt = datetime.fromisoformat(raw_str.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass

        # Formats like '2026-10-24 14:30:00'
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b %d, %Y", "%d %b %Y"):
            try:
                dt = datetime.strptime(raw_str, fmt)
                return dt.replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                continue

    return datetime.now(timezone.utc).isoformat()


def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Deduplicate articles by canonical URL and normalized title hash."""
    seen_urls = set()
    seen_hashes = set()
    unique_articles = []

    for art in articles:
        title = normalize_title(art.get("title", ""))
        if not title or len(title) < 5:
            continue

        raw_url = art.get("url") or ""
        canon_url = canonicalize_url(raw_url)
        art_hash = compute_article_hash(title, canon_url)

        if canon_url and canon_url in seen_urls:
            continue
        if art_hash in seen_hashes:
            continue

        if canon_url:
            seen_urls.add(canon_url)
        seen_hashes.add(art_hash)

        art_copy = dict(art)
        art_copy["title"] = title
        art_copy["url"] = canon_url or raw_url
        unique_articles.append(art_copy)

    return unique_articles


def fetch_raw_news(ticker: str, limit: int = 15) -> List[Dict]:
    """Fetch raw news articles with multi-provider fallback."""
    ticker_clean = ticker.upper().strip()
    articles = []

    # 1. Primary: yfinance news
    try:
        stock = yf.Ticker(ticker_clean)
        yf_news = stock.news or []
        for n in yf_news[:limit]:
            # Support both old and new yfinance news schema
            content = n.get("content") if isinstance(n.get("content"), dict) else {}
            title = n.get("title") or content.get("title") or ""
            link = n.get("link") or content.get("canonicalUrl", {}).get("url") or ""
            publisher = n.get("publisher") or content.get("provider", {}).get("displayName") or "Yahoo Finance"
            pub_time = n.get("providerPublishTime") or content.get("pubDate") or ""
            summary = n.get("summary") or content.get("summary") or ""

            if title:
                articles.append({
                    "ticker": ticker_clean,
                    "title": title,
                    "url": link,
                    "source": publisher,
                    "published_at": parse_publication_time(pub_time),
                    "description": summary,
                })
    except Exception:
        pass

    # 2. Secondary: NewsAPI fallback if available
    if not articles and getattr(Config, "NEWS_API_KEY", None):
        try:
            from news_fetcher import fetch_news_for_ticker
            api_news = fetch_news_for_ticker(ticker_clean)[:limit]
            for n in api_news:
                articles.append({
                    "ticker": ticker_clean,
                    "title": n.get("title", ""),
                    "url": n.get("url", ""),
                    "source": n.get("source") or "NewsAPI",
                    "published_at": parse_publication_time(n.get("published_at")),
                    "description": n.get("description", ""),
                })
        except Exception:
            pass

    # 3. Tertiary: Finnhub news fallback if key available
    if not articles:
        finnhub_key = os.getenv("FINNHUB_API_KEY", "").strip()
        if finnhub_key:
            try:
                category = "crypto" if ticker_clean.endswith("-USD") or "BTC" in ticker_clean else "general"
                resp = requests.get(
                    "https://finnhub.io/api/v1/news",
                    params={"category": category, "token": finnhub_key},
                    timeout=8,
                )
                if resp.status_code == 200:
                    for it in (resp.json() or [])[:limit]:
                        articles.append({
                            "ticker": ticker_clean,
                            "title": it.get("headline", ""),
                            "url": it.get("url", ""),
                            "source": it.get("source") or "Finnhub",
                            "published_at": parse_publication_time(it.get("datetime")),
                            "description": it.get("summary", ""),
                        })
            except Exception:
                pass

    # Deduplicate before returning
    return deduplicate_articles(articles)


def process_and_analyze_news(ticker: str, limit: int = 15) -> List[Dict]:
    """Fetch, deduplicate, cache-check, and analyze news articles for a ticker.

    Avoids reprocessing unchanged articles if already analyzed in database.
    Returns fully enriched articles with sentiment labels, scores, confidences,
    processing status, and publication times.
    """
    ticker_clean = ticker.upper().strip()
    analyzer = get_analyzer()

    # 1. Fetch raw articles from providers
    raw_articles = fetch_raw_news(ticker_clean, limit=limit)

    # 2. If no live articles could be fetched, fallback to existing database cache
    if not raw_articles:
        db_articles = database.get_news_with_latest_sentiment(ticker_clean)
        if db_articles:
            # Mark processing status as 'cached'
            for a in db_articles:
                if not a.get("processing_status"):
                    a["processing_status"] = "cached"
            return db_articles[:limit]
        return []

    processed = []
    new_articles_to_insert = []
    new_sentiments_to_insert = []

    for art in raw_articles:
        title = art["title"]
        url = art.get("url", "")
        pub_at = art.get("published_at")
        source = art.get("source", "Market Wire")
        description = art.get("description", "")

        # Check database cache by URL to avoid redundant FinBERT/VADER inference
        cached_sentiment = database.get_cached_sentiment_for_url(url)
        if cached_sentiment:
            processed.append({
                "ticker": ticker_clean,
                "title": title,
                "url": url,
                "source": source,
                "published_at": pub_at,
                "description": description,
                "sentiment_label": cached_sentiment.get("sentiment_label", "Neutral"),
                "sentiment_score": float(cached_sentiment.get("sentiment_score", 0.0)),
                "confidence": float(cached_sentiment.get("confidence", 0.5)),
                "model_name": cached_sentiment.get("model_name", "cached"),
                "processing_status": "cached",
                "analyzed_at": cached_sentiment.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
            })
            continue

        # New article: Run sentiment inference
        analysis = analyzer.analyze_headline(title)
        analyzed_at = datetime.now(timezone.utc).isoformat()
        sentiment_label = analysis.get("label", "Neutral")
        sentiment_score = float(analysis.get("score", 0.0))
        confidence = float(analysis.get("confidence", 0.5))
        model_name = analysis.get("model", "vader")

        item = {
            "ticker": ticker_clean,
            "title": title,
            "url": url,
            "source": source,
            "published_at": pub_at,
            "description": description,
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score,
            "confidence": confidence,
            "model_name": model_name,
            "processing_status": "analyzed",
            "analyzed_at": analyzed_at,
        }
        processed.append(item)
        new_articles_to_insert.append(item)

    # 3. Store new articles and sentiments in SQLite database for persistent caching
    if new_articles_to_insert:
        try:
            database.insert_articles(ticker_clean, new_articles_to_insert)
            for item in new_articles_to_insert:
                art_id = database.get_article_id_by_url(item.get("url"))
                if art_id:
                    database.insert_sentiment(
                        article_id=art_id,
                        model_name=item["model_name"],
                        label=item["sentiment_label"],
                        score=item["sentiment_score"],
                        confidence=item["confidence"],
                    )
        except Exception:
            pass

    return processed[:limit]
