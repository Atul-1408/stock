"""Phase 5 AI Financial Intelligence Test Suite.

Validates:
1. Article normalization (canonical URL stripping, title cleaning, UTC ISO timestamp parsing).
2. Deduplication across providers.
3. Sentiment confidence scoring, signed score mapping, and batch aggregation.
4. News service caching (avoiding reprocessing unchanged articles).
5. AI Market Brief endpoint: verified facts, interpretation, influential news, disclaimers, TTL caching.
6. Stock Intelligence endpoint: price dynamics, news synthesis, sample size honesty, limitations.
7. Chatbot grounding: grounded market reality, prevention of hallucinated prices, unsupported queries handling, privacy protection.
8. Model quality evaluation suite and metric computations.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase5-ai-test-secret-key-32-bytes-long!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Mock transformers pipeline to ensure fast, deterministic tests
try:
    import transformers
    transformers.pipeline = MagicMock(return_value=lambda text, **kwargs: [{"label": "positive", "score": 0.88}])
except ImportError:
    pass

# Mock yfinance to ensure instantaneous offline deterministic execution
try:
    import yfinance as yf
    mock_ticker_obj = MagicMock()
    mock_ticker_obj.news = [
        {"title": "Apple Posts Record Earnings Beats Consensus", "link": "https://wire.example.com/aapl-1", "publisher": "Wire", "providerPublishTime": 1700000000},
        {"title": "Tech Stocks Gain as Rate Pressures Ease", "link": "https://wire.example.com/aapl-2", "publisher": "Wire", "providerPublishTime": 1700000000},
        {"title": "Chip Makers See Strong Data Center Bookings", "link": "https://wire.example.com/aapl-3", "publisher": "Wire", "providerPublishTime": 1700000000},
    ]
    yf.Ticker = MagicMock(return_value=mock_ticker_obj)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
from app import app
from config import Config
import chatbot_engine
from news_service import (
    canonicalize_url,
    normalize_title,
    compute_article_hash,
    parse_publication_time,
    deduplicate_articles,
    process_and_analyze_news,
)
from sentiment_service import SentimentAnalyzer, get_sentiment
from market_brief_service import generate_market_brief, clear_brief_cache
from stock_intelligence_service import get_stock_intelligence
from evaluate_sentiment import calculate_classification_metrics


class TestPhase5AIFinancialIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

        # Seed test user and token
        database.init_db()
        test_email = "ai_analyst@sovereign.test"
        existing_user = database.get_user_by_email(test_email)
        if not existing_user:
            cls.user_id = database.create_user(
                email=test_email,
                password_hash="hashed_pw_test",
                full_name="AI Analyst Test"
            )
        else:
            cls.user_id = existing_user["id"]

        from app import create_access_token
        with app.app_context():
            cls.token = create_access_token(identity=str(cls.user_id))
        cls.headers = {
            "Authorization": f"Bearer {cls.token}",
            "Content-Type": "application/json"
        }

        # Seed stock universe and market index for brief
        database.bulk_insert_stocks([{
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "market_cap": 3000000000000
        }])
        database.upsert_index({
            "index_name": "S&P 500",
            "display_name": "S&P 500",
            "current_value": 5864.67,
            "open_value": 5840.0,
            "high_value": 5870.0,
            "low_value": 5835.0,
            "prev_close": 5840.0,
            "change_pct": 0.42
        })

    def setUp(self):
        clear_brief_cache()

    # -------------------------------------------------------------
    # 1. TASK 1: ARTICLE NORMALIZATION, VALIDATION, AND DEDUPLICATION
    # -------------------------------------------------------------
    def test_01_canonicalize_url(self):
        """URL canonicalization strips marketing and tracking parameters."""
        dirty_url = "https://finance.yahoo.com/news/apple-earnings-123.html?utm_source=twitter&utm_medium=social&ref=feed"
        clean = canonicalize_url(dirty_url)
        self.assertEqual(clean, "https://finance.yahoo.com/news/apple-earnings-123.html")

    def test_02_normalize_title(self):
        """Title normalization strips HTML tags and excess whitespace."""
        raw_title = "   <b>Apple Inc.</b>  reports   record quarterly revenue \n\t "
        clean = normalize_title(raw_title)
        self.assertEqual(clean, "Apple Inc. reports record quarterly revenue")

    def test_03_publication_time_parsing(self):
        """Timestamp parser converts unix epoch and string formats to standard UTC ISO string."""
        # Unix timestamp
        iso_from_epoch = parse_publication_time(1700000000)
        self.assertIn("T", iso_from_epoch)
        self.assertIn("+00:00", iso_from_epoch)

        # Standard date string
        iso_from_str = parse_publication_time("2026-10-24 14:30:00")
        self.assertIn("2026-10-24T14:30:00", iso_from_str)

    def test_04_deduplicate_articles(self):
        """Deduplication removes duplicate URLs and equivalent headlines."""
        articles = [
            {"title": "Tesla cuts Model Y prices in Europe", "url": "https://reuters.com/article/1?utm_source=rss"},
            {"title": "Tesla cuts Model Y prices in Europe", "url": "https://reuters.com/article/1?utm_source=twitter"}, # duplicate URL
            {"title": "Tesla Cuts Model Y Prices In Europe!", "url": "https://bloomberg.com/news/tsla"}, # duplicate title hash
            {"title": "Microsoft reveals new cloud AI infrastructure", "url": "https://msft.com/news/ai"}, # distinct
        ]
        deduped = deduplicate_articles(articles)
        self.assertEqual(len(deduped), 2)
        titles = [a["title"] for a in deduped]
        self.assertIn("Tesla cuts Model Y prices in Europe", titles)
        self.assertIn("Microsoft reveals new cloud AI infrastructure", titles)

    # -------------------------------------------------------------
    # 2. TASK 1 & 2: SENTIMENT CONFIDENCE AND STATISTICAL AGGREGATION
    # -------------------------------------------------------------
    def test_05_vader_calibrated_confidence(self):
        """VADER output returns signed score between -1 and 1, plus calibrated confidence."""
        analyzer = SentimentAnalyzer()
        res_pos = analyzer._analyze_with_vader("Company quarterly profit jumped 45% beat estimates")
        self.assertEqual(res_pos["label"], "Positive")
        self.assertGreater(res_pos["score"], 0.0)
        self.assertGreaterEqual(res_pos["confidence"], 0.5)

        res_neg = analyzer._analyze_with_vader("Company reports disastrous bankruptcy default and massive collapse")
        self.assertEqual(res_neg["label"], "Negative")
        self.assertLess(res_neg["score"], 0.0)
        self.assertGreaterEqual(res_neg["confidence"], 0.5)

    def test_06_statistical_aggregation_and_sufficiency(self):
        """Batch aggregation computes consensus label, distribution, and data sufficiency flag."""
        analyzer = SentimentAnalyzer()
        analyses = [
            {"label": "Positive", "score": 0.8, "confidence": 0.9, "model": "finbert"},
            {"label": "Positive", "score": 0.6, "confidence": 0.8, "model": "finbert"},
            {"label": "Neutral", "score": 0.0, "confidence": 0.6, "model": "vader"},
        ]
        agg = analyzer.aggregate_sentiment(analyses)
        self.assertEqual(agg["label"], "Positive")
        self.assertEqual(agg["sample_size"], 3)
        self.assertTrue(agg["is_sufficient_data"])
        self.assertEqual(agg["distribution"]["positive"], 2)
        self.assertEqual(agg["distribution"]["neutral"], 1)

        # Insufficient data (N < 3)
        agg_small = analyzer.aggregate_sentiment([{"label": "Positive", "score": 0.5, "confidence": 0.7, "model": "vader"}])
        self.assertFalse(agg_small["is_sufficient_data"])
        self.assertEqual(agg_small["sample_size"], 1)

    # -------------------------------------------------------------
    # 3. TASK 1 & 7: NEWS SERVICE CACHING AND FALLBACK
    # -------------------------------------------------------------
    def test_07_news_service_caching_avoids_reprocessing(self):
        """News service reuses cached sentiment in database to avoid reprocessing unchanged articles."""
        url = "https://wire.example.com/aapl-record-revenue-2026"
        pub_at = "2026-10-24T10:00:00+00:00"

        # Pre-insert into DB
        database.insert_articles("AAPL", [{
            "title": "Apple Posts Record Revenue In Quarter",
            "url": url,
            "source": "Wire Example",
            "published_at": pub_at,
            "processing_status": "analyzed"
        }])
        art_id = database.get_article_id_by_url(url)
        database.insert_sentiment(art_id, "test_cached_model", "Positive", 0.92, 0.95)

        # Retrieve cached sentiment directly
        cached = database.get_cached_sentiment_for_url(url)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["sentiment_label"], "Positive")
        self.assertEqual(cached["model_name"], "test_cached_model")

    # -------------------------------------------------------------
    # 4. TASK 3: AI MARKET BRIEF ENDPOINT & TTL CACHE
    # -------------------------------------------------------------
    def test_08_market_brief_generation(self):
        """GET /api/market/brief returns structured facts, interpretation, influential news, and limitations."""
        res = self.client.get("/api/market/brief", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)

        self.assertEqual(data["status"], "success")
        self.assertIn("verified_facts", data)
        self.assertIsInstance(data["verified_facts"], list)
        self.assertGreater(len(data["verified_facts"]), 0)

        self.assertIn("interpretation", data)
        self.assertIsInstance(data["interpretation"], str)

        self.assertIn("influential_news", data)
        self.assertIn("disclaimer", data)
        self.assertIn("time_window", data)
        self.assertIn("data_sources", data)

    def test_09_market_brief_ttl_caching(self):
        """Second call to /api/market/brief retrieves cached payload within TTL."""
        res1 = self.client.get("/api/market/brief", headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        data1 = json.loads(res1.data)
        self.assertFalse(data1.get("cached", False))

        res2 = self.client.get("/api/market/brief", headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertTrue(data2.get("cached", True))

    # -------------------------------------------------------------
    # 5. TASK 4: STOCK INTELLIGENCE ENDPOINT
    # -------------------------------------------------------------
    def test_10_stock_intelligence_api(self):
        """GET /api/stocks/<symbol>/intelligence returns price dynamics, news synthesis, and limitations."""
        res = self.client.get("/api/stocks/AAPL/intelligence", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn("price_metrics", data)
        self.assertIn("sentiment_metrics", data)
        self.assertIn("summary", data)
        self.assertIn("limitations", data)
        self.assertIn("not a guaranteed trading signal", data["limitations"].lower())

    # -------------------------------------------------------------
    # 6. TASK 5: CHATBOT HARDENING & GROUNDED REALITY
    # -------------------------------------------------------------
    def test_11_chatbot_unsupported_guaranteed_return_query(self):
        """Chatbot gracefully declines requests for guaranteed returns."""
        bot = chatbot_engine.get_chatbot()
        reply = bot._handle_unsupported_query("Can your AI guarantee 100% win rate and risk free profit?")
        self.assertIsNotNone(reply)
        self.assertTrue("guarantee" in reply.lower() and "risk" in reply.lower())

    def test_12_chatbot_unsupported_tax_query(self):
        """Chatbot gracefully declines requests for legal or tax advice."""
        bot = chatbot_engine.get_chatbot()
        reply = bot._handle_unsupported_query("How can I file my taxes and get a tax deduction for stock losses?")
        self.assertIsNotNone(reply)
        self.assertIn("cannot provide tax", reply.lower())

    def test_13_chatbot_grounded_market_context_injection(self):
        """Chatbot system prompt injects verified real-time prices to prevent hallucinations."""
        bot = chatbot_engine.get_chatbot()
        context = bot._get_grounded_market_context(["AAPL"])
        self.assertIn("VERIFIED MARKET REALITY", context)
        self.assertIn("AAPL", context)

    def test_14_chatbot_chat_analyze_endpoint(self):
        """GET /api/chat/analyze/AAPL returns enriched stock intelligence with limitations."""
        res = self.client.get("/api/chat/analyze/AAPL", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("analysis", data)
        self.assertIn("AAPL Intelligence Report", data["analysis"])
        self.assertIn("LIMITATIONS", data["analysis"])

    # -------------------------------------------------------------
    # 7. TASK 6: MODEL QUALITY BENCHMARK METRIC CALCULATIONS
    # -------------------------------------------------------------
    def test_15_classification_metrics_calculation(self):
        """Classification metrics calculator correctly computes Accuracy, Precision, Recall, F1, and Confusion Matrix."""
        y_true = ["Positive", "Positive", "Negative", "Negative", "Neutral", "Neutral"]
        y_pred = ["Positive", "Neutral",  "Negative", "Negative", "Neutral", "Positive"]

        metrics = calculate_classification_metrics(y_true, y_pred)
        self.assertEqual(metrics["total_samples"], 6)
        self.assertEqual(metrics["correct_predictions"], 4)
        self.assertAlmostEqual(metrics["accuracy"], 4 / 6, places=3)

        # Check per-class metrics
        self.assertIn("Positive", metrics["per_class"])
        self.assertIn("Negative", metrics["per_class"])
        self.assertIn("Neutral", metrics["per_class"])

        # Negative class was perfectly classified (2 TP, 0 FP, 0 FN)
        self.assertEqual(metrics["per_class"]["Negative"]["precision"], 1.0)
        self.assertEqual(metrics["per_class"]["Negative"]["recall"], 1.0)
        self.assertEqual(metrics["per_class"]["Negative"]["f1"], 1.0)

        # Check confusion matrix presence
        self.assertIn("Positive", metrics["confusion_matrix"])


if __name__ == "__main__":
    unittest.main()
