"""Sentiment analysis using FinBERT with VADER fallback.

Primary model: ProsusAI/finbert (Hugging Face)
Fallback model: VADER
"""

from typing import Dict

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config import Config


class SentimentAnalyzer:
    """Analyze financial-news sentiment with FinBERT and fallback to VADER."""

    def __init__(self) -> None:
        self._finbert_pipeline = None
        self._vader = SentimentIntensityAnalyzer()

        # Lazy-load FinBERT so app startup is fast and resilient.
        try:
            from transformers import pipeline

            self._finbert_pipeline = pipeline(
                task="text-classification",
                model=Config.FINBERT_MODEL_NAME,
                tokenizer=Config.FINBERT_MODEL_NAME,
            )
        except Exception:
            # If model download/load fails, VADER fallback will still work.
            self._finbert_pipeline = None

    @staticmethod
    def _normalize_label(label: str) -> str:
        """Convert raw labels to clean title-case labels."""
        cleaned = (label or "").strip().lower()
        if cleaned == "positive":
            return "Positive"
        if cleaned == "negative":
            return "Negative"
        return "Neutral"

    def _analyze_with_finbert(self, headline: str) -> Dict:
        """Run FinBERT inference and return normalized output with calibrated confidence."""
        if self._finbert_pipeline is None:
            raise RuntimeError("FinBERT pipeline is not available.")

        result = self._finbert_pipeline(headline, truncation=True)[0]
        label = self._normalize_label(result.get("label", "Neutral"))
        prob = float(result.get("score", 0.0))

        # Signed score: +prob for positive, -prob for negative, 0.0 for neutral
        if label == "Positive":
            signed_score = prob
        elif label == "Negative":
            signed_score = -prob
        else:
            signed_score = 0.0

        return {
            "model": "finbert",
            "label": label,
            "score": round(signed_score, 4),
            "confidence": round(prob, 4),
        }

    def _analyze_with_vader(self, headline: str) -> Dict:
        """Run VADER inference and return signed score and calibrated confidence."""
        scores = self._vader.polarity_scores(headline)
        compound = float(scores.get("compound", 0.0))

        if compound >= 0.05:
            label = "Positive"
            confidence = min(1.0, 0.5 + abs(compound) * 0.5)
        elif compound <= -0.05:
            label = "Negative"
            confidence = min(1.0, 0.5 + abs(compound) * 0.5)
        else:
            label = "Neutral"
            confidence = max(0.5, 1.0 - abs(compound) * 5.0)

        return {
            "model": "vader",
            "label": label,
            "score": round(compound, 4),
            "confidence": round(confidence, 4),
        }

    def analyze_headline(self, headline: str) -> Dict:
        """Analyze one headline.

        Input:
            headline (str)
        Returns:
            {
              "label": "Positive|Negative|Neutral",
              "score": float between -1.0 and 1.0,
              "confidence": float between 0.0 and 1.0,
              "model": "finbert|vader"
            }
        """
        text = (headline or "").strip()
        if not text:
            return {"label": "Neutral", "score": 0.0, "confidence": 0.5, "model": "vader"}

        try:
            return self._analyze_with_finbert(text)
        except Exception:
            return self._analyze_with_vader(text)

    def analyze_headlines(self, headlines: list) -> list:
        """Analyze a list of headlines and return analysis for each."""
        return [self.analyze_headline(h) for h in headlines if (h or "").strip()]

    @staticmethod
    def aggregate_sentiment(analyses: list) -> Dict:
        """Aggregate multiple headline analyses into a statistical summary."""
        if not analyses:
            return {
                "label": "Neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model": "vader",
                "sample_size": 0,
                "is_sufficient_data": False,
                "distribution": {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0,
                    "pos_pct": 0.0,
                    "neu_pct": 100.0,
                    "neg_pct": 0.0,
                },
            }

        pos_count = sum(1 for a in analyses if a.get("label") == "Positive")
        neg_count = sum(1 for a in analyses if a.get("label") == "Negative")
        neu_count = sum(1 for a in analyses if a.get("label") == "Neutral")
        total = len(analyses)

        scores = [float(a.get("score", 0.0)) for a in analyses]
        confidences = [float(a.get("confidence", 0.5)) for a in analyses]
        mean_score = sum(scores) / total if total > 0 else 0.0
        mean_confidence = sum(confidences) / total if total > 0 else 0.0

        if mean_score >= 0.15:
            consensus_label = "Positive"
        elif mean_score <= -0.15:
            consensus_label = "Negative"
        else:
            consensus_label = "Neutral"

        models = [a.get("model", "vader") for a in analyses]
        dominant_model = "finbert" if models.count("finbert") > models.count("vader") else "vader"

        return {
            "label": consensus_label,
            "score": round(mean_score, 4),
            "confidence": round(mean_confidence, 4),
            "model": dominant_model,
            "sample_size": total,
            "is_sufficient_data": total >= 3,
            "distribution": {
                "positive": pos_count,
                "neutral": neu_count,
                "negative": neg_count,
                "pos_pct": round((pos_count / total) * 100, 1),
                "neu_pct": round((neu_count / total) * 100, 1),
                "neg_pct": round((neg_count / total) * 100, 1),
            },
        }


# Global instance for easy access
_analyzer = None


def get_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


def get_sentiment(ticker: str) -> Dict:
    """Helper to get aggregate sentiment for a ticker from available news headlines."""
    analyzer = get_analyzer()

    try:
        stock = yf.Ticker(ticker.upper())
        news = stock.news or []
        headlines = []
        for n in news[:10]:
            title = n.get("title") or (n.get("content", {}) if isinstance(n.get("content"), dict) else {}).get("title")
            if title:
                headlines.append(title)

        if not headlines:
            return {
                "label": "Neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model": "vader",
                "sample_size": 0,
                "is_sufficient_data": False,
                "distribution": {"positive": 0, "neutral": 0, "negative": 0, "pos_pct": 0, "neu_pct": 100, "neg_pct": 0},
            }

        analyses = analyzer.analyze_headlines(headlines)
        return analyzer.aggregate_sentiment(analyses)
    except Exception as e:
        print(f"Error in get_sentiment for {ticker}: {e}")
        return {
            "label": "Neutral",
            "score": 0.0,
            "confidence": 0.0,
            "model": "vader",
            "sample_size": 0,
            "is_sufficient_data": False,
            "distribution": {"positive": 0, "neutral": 0, "negative": 0, "pos_pct": 0, "neu_pct": 100, "neg_pct": 0},
        }
