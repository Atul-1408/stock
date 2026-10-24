"""Stock Intelligence Service.

Generates concise, factual summaries of recent price movement and news sentiment
for individual equities.
- Avoids presenting sentiment as a guaranteed trading signal.
- Honestly reports sample size and data sufficiency.
- Highlights important analytical limitations and risk disclosures.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import math

import database
from news_service import process_and_analyze_news
from trading_engine import get_current_price


def get_stock_intelligence(ticker: str) -> Dict:
    """Generate a comprehensive stock intelligence report for a ticker.

    Returns:
        {
            "ticker": "AAPL",
            "as_of": "<ISO8601>",
            "price_metrics": {...},
            "sentiment_metrics": {...},
            "summary": "...",
            "influencing_headlines": [...],
            "limitations": "..."
        }
    """
    ticker_clean = ticker.upper().strip()

    # 1. Price Movement Metrics
    current_price = get_current_price(ticker_clean) or 0.0
    price_rows = database.get_prices_last_30_days(ticker_clean) or []

    # Sort chronological
    sorted_prices = sorted(price_rows, key=lambda x: str(x.get("trade_date", "")))
    close_prices = [float(p.get("close", 0.0)) for p in sorted_prices if p.get("close") is not None]

    price_metrics = {
        "current_price": round(current_price, 2),
        "data_points": len(close_prices),
        "has_price_data": len(close_prices) > 0,
        "change_7d_pct": 0.0,
        "change_30d_pct": 0.0,
        "high_30d": round(max(close_prices), 2) if close_prices else round(current_price, 2),
        "low_30d": round(min(close_prices), 2) if close_prices else round(current_price, 2),
        "trend": "Neutral",
    }

    if len(close_prices) >= 2:
        start_price = close_prices[0]
        end_price = close_prices[-1]
        price_metrics["change_30d_pct"] = round(((end_price - start_price) / start_price) * 100, 2)

        p7_index = max(0, len(close_prices) - 7)
        p7_start = close_prices[p7_index]
        price_metrics["change_7d_pct"] = round(((end_price - p7_start) / p7_start) * 100, 2)

        if price_metrics["change_7d_pct"] >= 2.0:
            price_metrics["trend"] = "Uptrend"
        elif price_metrics["change_7d_pct"] <= -2.0:
            price_metrics["trend"] = "Downtrend"
        else:
            price_metrics["trend"] = "Consolidating"

    # 2. News and Sentiment Analysis
    articles = process_and_analyze_news(ticker_clean, limit=10)
    total_articles = len(articles)

    pos_count = sum(1 for a in articles if a.get("sentiment_label") == "Positive")
    neg_count = sum(1 for a in articles if a.get("sentiment_label") == "Negative")
    neu_count = sum(1 for a in articles if a.get("sentiment_label") == "Neutral")

    if total_articles > 0:
        avg_score = sum(float(a.get("sentiment_score", 0.0)) for a in articles) / total_articles
        avg_confidence = sum(float(a.get("confidence", 0.5)) for a in articles) / total_articles
        pos_pct = round((pos_count / total_articles) * 100, 1)
        neg_pct = round((neg_count / total_articles) * 100, 1)
        neu_pct = round((neu_count / total_articles) * 100, 1)
        is_sufficient = total_articles >= 3
    else:
        avg_score = 0.0
        avg_confidence = 0.0
        pos_pct, neg_pct, neu_pct = 0.0, 0.0, 100.0
        is_sufficient = False

    sentiment_metrics = {
        "score": round(avg_score, 4),
        "label": "Positive" if avg_score >= 0.15 else "Negative" if avg_score <= -0.15 else "Neutral",
        "confidence": round(avg_confidence, 4),
        "sample_size": total_articles,
        "is_sufficient_data": is_sufficient,
        "data_sufficiency_warning": None if is_sufficient else f"Low headline sample size (N={total_articles}). Sentiment may not be statistically robust.",
        "distribution": {
            "positive": pos_count,
            "neutral": neu_count,
            "negative": neg_count,
            "pos_pct": pos_pct,
            "neu_pct": neu_pct,
            "neg_pct": neg_pct,
        },
    }

    # 3. Concise Factual Summary
    summary_parts = []
    if current_price > 0:
        summary_parts.append(
            f"{ticker_clean} is currently trading at ${current_price:.2f}."
        )
        if len(close_prices) >= 2:
            summary_parts.append(
                f"Over the last 7 trading days, price moved {price_metrics['change_7d_pct']:+.2f}% ({price_metrics['trend']}), "
                f"within a 30-day range of ${price_metrics['low_30d']:.2f} - ${price_metrics['high_30d']:.2f}."
            )

    if total_articles > 0:
        summary_parts.append(
            f"Sentiment across {total_articles} recent media dispatches is {sentiment_metrics['label']} "
            f"(composite index: {avg_score:+.2f}, {pos_count} positive, {neu_count} neutral, {neg_count} negative)."
        )
    else:
        summary_parts.append("No recent news articles were indexed for this symbol in active feeds.")

    # 4. Influencing Headlines
    influencing_headlines = []
    for art in articles[:4]:
        influencing_headlines.append({
            "title": art.get("title"),
            "source": art.get("source"),
            "url": art.get("url"),
            "published_at": art.get("published_at"),
            "sentiment_label": art.get("sentiment_label"),
            "sentiment_score": float(art.get("sentiment_score", 0.0)),
            "confidence": float(art.get("confidence", 0.5)),
        })

    return {
        "status": "success",
        "ticker": ticker_clean,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "price_metrics": price_metrics,
        "sentiment_metrics": sentiment_metrics,
        "summary": " ".join(summary_parts),
        "influencing_headlines": influencing_headlines,
        "limitations": (
            "IMPORTANT LIMITATIONS: Sentiment analysis measures linguistic tone in public news articles and does not "
            "account for company balance sheets, intrinsic valuation, debt structure, or macroeconomic shifts. "
            "Sentiment is NOT a guaranteed trading signal, and sudden price reversals can occur regardless of media sentiment."
        ),
    }
