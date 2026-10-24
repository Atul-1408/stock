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
        """Run FinBERT inference and return normalized output."""
        if self._finbert_pipeline is None:
            raise RuntimeError("FinBERT pipeline is not available.")

        result = self._finbert_pipeline(headline, truncation=True)[0]
        return {
            "model": "finbert",
            "label": self._normalize_label(result.get("label", "Neutral")),
            "score": float(result.get("score", 0.0)),
        }

    def _analyze_with_vader(self, headline: str) -> Dict:
        """Run VADER inference and map compound score to label."""
        scores = self._vader.polarity_scores(headline)
        compound = float(scores.get("compound", 0.0))

        if compound >= 0.05:
            label = "Positive"
            confidence = compound
        elif compound <= -0.05:
            label = "Negative"
            confidence = abs(compound)
        else:
            label = "Neutral"
            confidence = 1.0 - abs(compound)

        return {
            "model": "vader",
            "label": label,
            "score": max(0.0, min(1.0, confidence)),
        }

    def analyze_headline(self, headline: str) -> Dict:
        """Analyze one headline.

        Input:
            headline (str)
        Returns:
            {
              "label": "Positive|Negative|Neutral",
              "score": float between 0 and 1,
              "model": "finbert|vader"
            }
        """
        text = (headline or "").strip()
        if not text:
            return {"label": "Neutral", "score": 0.0, "model": "vader"}

        try:
            return self._analyze_with_finbert(text)
        except Exception:
            return self._analyze_with_vader(text)

# Global instance for easy access
_analyzer = None

def get_sentiment(ticker: str) -> Dict:
    """Helper to get sentiment for a ticker (analyzes first news headline)."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    
    try:
        stock = yf.Ticker(ticker.upper())
        news = stock.news
        if not news:
            return {"label": "Neutral", "score": 0.0, "model": "vader"}
        
        # Analyze the latest headline
        headline = news[0].get("title", "")
        return _analyzer.analyze_headline(headline)
    except Exception as e:
        print(f"Error in get_sentiment for {ticker}: {e}")
        return {"label": "Neutral", "score": 0.0, "model": "vader"}
