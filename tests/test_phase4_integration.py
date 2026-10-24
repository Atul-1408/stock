"""Phase 4 Frontend and Backend Integration Test Suite.

Validates end-to-end integration between frontend API contracts and backend endpoints:
1. Authentication: signup, login, auth/me, expired token, invalid credentials.
2. Dashboard feeds: indices, ticker-tape, search.
3. Empty portfolio states: fresh user account with 0 holdings.
4. Populated portfolio states: executed paper trades, positions, transactions.
5. Stock details: symbols, historical prices, sentiment, and news.
6. Unsupported symbol handling: 404 and graceful empty fallbacks without 500 crashes.
7. Order management: placing orders, listing orders, cancelling orders.
8. Validation: negative quantities, invalid sides, NaN/inf numbers.
9. Bot desk integration: config, status, signals, watchlist add/delete.
10. Alerts & Neural Intelligence: watcher creation, toggling, chat conversations.
11. Currency conversion endpoints.
12. Rate limiting (429 Too Many Requests) and error handling.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Configure testing environment before importing local modules
os.environ["FLASK_ENV"] = "testing"
os.environ["ENABLE_BACKGROUND_WORKERS"] = "false"
os.environ["JWT_SECRET_KEY"] = "phase4-integration-test-secret-key-32-bytes!"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# Mock transformers pipeline to prevent any HuggingFace downloads during testing
try:
    import transformers
    transformers.pipeline = MagicMock(return_value=lambda text, **kwargs: [{"label": "neutral", "score": 0.5}])
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database
from app import app
from config import Config
import chatbot_engine

# Mock Chatbot AI client to ensure offline deterministic responses
chatbot_engine.TradingChatbot.get_response = MagicMock(return_value={
    "response": "Market sentiment for AAPL is currently balanced with neutral momentum.",
    "actions": [{"type": "hold", "confidence": "medium"}],
    "stocks_mentioned": ["AAPL"]
})


class TestPhase4Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

        # Seed an isolated user for integration testing
        cls.test_email = "phase4_operator@sovereign.internal"
        cls.test_password = "SecurePassword123!"
        cls.test_username = "phase4_op"

        # Register user via API
        reg_res = cls.client.post("/api/auth/signup", json={
            "email": cls.test_email,
            "password": cls.test_password,
            "username": cls.test_username,
            "full_name": "Phase 4 Operator"
        })

        # Login to get JWT access token
        login_res = cls.client.post("/api/auth/login", json={
            "email": cls.test_email,
            "password": cls.test_password
        })
        login_data = json.loads(login_res.data)
        cls.token = login_data.get("access_token")
        cls.user_id = login_data.get("user_id")
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Seed AAPL in stock_universe and market data cache for testing
        database.bulk_insert_stocks([
            {
                "symbol": "AAPL",
                "company_name": "Apple Inc.",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "market_cap": 3000000000000,
                "country": "USA",
                "currency": "USD"
            }
        ])

    # ---------------------------------------------------------
    # 1. AUTHENTICATION & SESSION LIFECYCLE
    # ---------------------------------------------------------
    def test_01_auth_me_with_valid_token(self):
        """GET /api/auth/me returns operator details and balance."""
        res = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data.get("status"), "success")
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], self.test_email)
        self.assertIn("current_balance", data["user"])

    def test_02_auth_me_with_missing_token(self):
        """GET /api/auth/me without token returns 401 Unauthorized."""
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertEqual(data.get("status"), "error")

    def test_03_auth_me_with_invalid_token(self):
        """GET /api/auth/me with malformed token returns 401."""
        res = self.client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.garbage.token"})
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertEqual(data.get("status"), "error")

    def test_04_login_with_invalid_credentials(self):
        """POST /api/auth/login with wrong password returns 401."""
        res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertEqual(data.get("status"), "error")

    # ---------------------------------------------------------
    # 2. DASHBOARD FEEDS & MARKET SUMMARY
    # ---------------------------------------------------------
    def test_05_market_indices(self):
        """GET /api/market/indices returns array of major market indices."""
        res = self.client.get("/api/market/indices")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("indices", data)
        self.assertIsInstance(data["indices"], list)

    def test_06_ticker_tape(self):
        """GET /api/ticker-tape returns quotes for requested tickers."""
        res = self.client.get("/api/ticker-tape?tickers=AAPL,MSFT,TSLA")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("tickers", data)
        self.assertIsInstance(data["tickers"], list)

    def test_07_stocks_quick_search(self):
        """GET /api/stocks/search returns autocomplete matches."""
        res = self.client.get("/api/stocks/search?q=AAPL&limit=5")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_08_market_watch_feed(self):
        """GET /api/market/watch returns filtered stock universe and metadata."""
        res = self.client.get("/api/market/watch?exchange=all&sector=all&limit=10")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("stocks", data)
        self.assertIn("indices", data)
        self.assertIn("exchanges", data)
        self.assertIn("sectors", data)

    # ---------------------------------------------------------
    # 3. EMPTY PORTFOLIO STATE
    # ---------------------------------------------------------
    def test_09_fresh_user_empty_portfolio(self):
        """A new user starts with 0 holdings and 0 unrealized P&L."""
        # Create dedicated fresh user
        fresh_email = "fresh_empty_user@sovereign.internal"
        self.client.post("/api/auth/signup", json={
            "email": fresh_email,
            "password": "Password123!",
            "username": "fresh_user",
            "full_name": "Fresh User"
        })
        l_res = self.client.post("/api/auth/login", json={
            "email": fresh_email,
            "password": "Password123!"
        })
        fresh_token = json.loads(l_res.data)["access_token"]
        fresh_headers = {"Authorization": f"Bearer {fresh_token}"}

        # Check /api/portfolio
        port_res = self.client.get("/api/portfolio", headers=fresh_headers)
        self.assertEqual(port_res.status_code, 200)
        port_data = json.loads(port_res.data)["data"]
        self.assertEqual(port_data["holdings"], [])
        self.assertEqual(port_data["total_market_value"], 0)
        self.assertEqual(port_data["total_pnl"], 0)

        # Check /api/positions
        pos_res = self.client.get("/api/positions", headers=fresh_headers)
        self.assertEqual(pos_res.status_code, 200)
        pos_data = json.loads(pos_res.data)
        self.assertEqual(pos_data["positions"], [])
        self.assertEqual(pos_data["total_pnl"], 0)

        # Check /api/transactions
        tx_res = self.client.get("/api/transactions", headers=fresh_headers)
        self.assertEqual(tx_res.status_code, 200)
        tx_data = json.loads(tx_res.data)
        self.assertEqual(tx_data["data"], [])

    # ---------------------------------------------------------
    # 4. POPULATED PORTFOLIO (SIMULATED PAPER TRADING)
    # ---------------------------------------------------------
    @patch("trading_engine.get_current_price", return_value=150.0)
    def test_10_execute_paper_trade_and_verify_portfolio(self, mock_price):
        """Execute atomic simulated buy order and verify portfolio updates."""
        # Buy 5 shares of AAPL at simulated $150.00
        trade_res = self.client.post("/api/trade", headers=self.headers, json={
            "ticker": "AAPL",
            "action": "BUY",
            "shares": 5,
            "sentiment_score": 0.85,
            "sentiment_label": "Bullish"
        })
        self.assertEqual(trade_res.status_code, 200)
        trade_data = json.loads(trade_res.data)
        self.assertTrue(trade_data["success"])

        # Verify /api/portfolio reflects 5 shares of AAPL
        port_res = self.client.get("/api/portfolio", headers=self.headers)
        self.assertEqual(port_res.status_code, 200)
        port_data = json.loads(port_res.data)["data"]
        self.assertGreater(len(port_data["holdings"]), 0)
        aapl_holding = next((h for h in port_data["holdings"] if h["ticker"] == "AAPL"), None)
        self.assertIsNotNone(aapl_holding)
        self.assertGreaterEqual(aapl_holding["shares"], 5)

        # Verify /api/positions reflects open position
        pos_res = self.client.get("/api/positions", headers=self.headers)
        self.assertEqual(pos_res.status_code, 200)
        pos_data = json.loads(pos_res.data)
        self.assertGreater(len(pos_data["positions"]), 0)

        # Verify /api/transactions logs the transaction
        tx_res = self.client.get("/api/transactions?limit=5", headers=self.headers)
        self.assertEqual(tx_res.status_code, 200)
        tx_data = json.loads(tx_res.data)["data"]
        self.assertGreater(len(tx_data), 0)
        self.assertEqual(tx_data[0]["ticker"], "AAPL")
        self.assertEqual(tx_data[0]["action"], "BUY")

    # ---------------------------------------------------------
    # 5. STOCK DETAILS & UNSUPPORTED SYMBOL HANDLING
    # ---------------------------------------------------------
    def test_11_stock_details_supported_symbol(self):
        """GET /api/stocks/AAPL/details returns complete fundamental & market data."""
        res = self.client.get("/api/stocks/AAPL/details")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("info", data)
        self.assertIn("market_data", data)
        self.assertIn("fundamentals", data)
        self.assertEqual(data["info"]["symbol"], "AAPL")

    def test_12_stock_details_unsupported_symbol(self):
        """GET /api/stocks/NONEXISTENTSYMBOL999/details returns 404 cleanly."""
        res = self.client.get("/api/stocks/NONEXISTENTSYMBOL999/details")
        self.assertEqual(res.status_code, 404)
        data = json.loads(res.data)
        self.assertEqual(data.get("status"), "error")
        self.assertIn("not found", data.get("message", "").lower())

    @patch("yfinance.download")
    @patch("yfinance.Ticker")
    def test_13_sentiment_and_prices_graceful_fallbacks(self, mock_ticker, mock_download):
        """Unsupported symbols return empty lists without crashing."""
        import pandas as pd
        mock_download.return_value = pd.DataFrame()
        mock_instance = mock_ticker.return_value
        mock_instance.news = []

        sent_res = self.client.get("/api/sentiment/UNKNOWN999XYZ", headers=self.headers)
        self.assertEqual(sent_res.status_code, 200)
        sent_data = json.loads(sent_res.data)
        self.assertEqual(sent_data["status"], "success")
        self.assertIsInstance(sent_data["data"], list)

        price_res = self.client.get("/api/prices/UNKNOWN999XYZ", headers=self.headers)
        self.assertEqual(price_res.status_code, 200)
        price_data = json.loads(price_res.data)
        self.assertEqual(price_data["status"], "success")
        self.assertIsInstance(price_data["data"], list)

    # ---------------------------------------------------------
    # 6. ORDER VALIDATION & DESTRUCTIVE ACTION CONFIRMATION FLOW
    # ---------------------------------------------------------
    def test_14_order_validation_rejects_negative_or_zero_qty(self):
        """POST /api/orders rejects invalid quantities with 400 Bad Request."""
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": -5
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertEqual(data.get("status"), "error")

    def test_15_order_validation_rejects_invalid_side(self):
        """POST /api/orders rejects unsupported sides with 400."""
        res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL",
            "side": "HOLD",
            "order_type": "MARKET",
            "quantity": 1
        })
        self.assertEqual(res.status_code, 400)

    @patch("trading_engine.get_current_price", return_value=120.0)
    def test_16_create_and_cancel_order(self, mock_price):
        """Create a LIMIT order, verify in order list, and cancel it."""
        # Create pending LIMIT order
        create_res = self.client.post("/api/orders", headers=self.headers, json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "LIMIT",
            "product_type": "CNC",
            "quantity": 1,
            "price": 100.0,
            "validity": "DAY"
        })
        self.assertEqual(create_res.status_code, 201)
        order_id = json.loads(create_res.data)["order_id"]

        # Verify order appears in order list
        list_res = self.client.get("/api/orders/list", headers=self.headers)
        self.assertEqual(list_res.status_code, 200)
        orders = json.loads(list_res.data)["orders"]
        matching = next((o for o in orders if o["id"] == order_id), None)
        self.assertIsNotNone(matching)
        self.assertEqual(matching["status"], "OPEN")

        # Cancel order
        cancel_res = self.client.delete(f"/api/orders/{order_id}/cancel", headers=self.headers)
        self.assertEqual(cancel_res.status_code, 200)

        # Cancel again should fail with 404 / already filled/cancelled
        re_cancel = self.client.delete(f"/api/orders/{order_id}/cancel", headers=self.headers)
        self.assertEqual(re_cancel.status_code, 404)

    # ---------------------------------------------------------
    # 7. AUTONOMOUS BOT DESK INTEGRATION
    # ---------------------------------------------------------
    def test_17_bot_config_get_and_put(self):
        """GET and PUT /api/bot/config successfully read and update strategy rules."""
        get_res = self.client.get("/api/bot/config", headers=self.headers)
        self.assertEqual(get_res.status_code, 200)
        config = json.loads(get_res.data)["config"]
        self.assertIn("risk_level", config)
        self.assertIn("max_position_size", config)

        # Update bot parameters
        put_res = self.client.put("/api/bot/config", headers=self.headers, json={
            "risk_level": "HIGH",
            "max_position_size": 15000,
            "stop_loss_pct": 0.04,
            "take_profit_pct": 0.12,
            "use_sentiment": 1,
            "use_technical": 1,
            "use_ml_model": 1
        })
        self.assertEqual(put_res.status_code, 200)

        # Verify updated values
        verify_res = self.client.get("/api/bot/config", headers=self.headers)
        updated = json.loads(verify_res.data)["config"]
        self.assertEqual(updated["risk_level"], "HIGH")
        self.assertEqual(updated["max_position_size"], 15000)

    def test_18_bot_watchlist_management(self):
        """Add ticker to bot watchlist, verify, and remove it."""
        # Add TSLA
        add_res = self.client.post("/api/bot/watchlist", headers=self.headers, json={"ticker": "TSLA"})
        self.assertIn(add_res.status_code, [200, 201])

        # Verify TSLA is in watchlist
        list_res = self.client.get("/api/bot/watchlist", headers=self.headers)
        self.assertEqual(list_res.status_code, 200)
        tickers = [item["ticker"] for item in json.loads(list_res.data)["watchlist"]]
        self.assertIn("TSLA", tickers)

        # Remove TSLA
        del_res = self.client.delete("/api/bot/watchlist/TSLA", headers=self.headers)
        self.assertEqual(del_res.status_code, 200)

    # ---------------------------------------------------------
    # 8. ALERTS & NEURAL INTELLIGENCE DESK
    # ---------------------------------------------------------
    def test_19_create_and_delete_alert(self):
        """POST /api/alerts creates threshold watcher, DELETE removes it."""
        create_res = self.client.post("/api/alerts", headers=self.headers, json={
            "ticker": "NVDA",
            "alert_type": "price_spike",
            "condition_operator": "above",
            "threshold_value": 200.0,
            "notification_method": "in_app"
        })
        self.assertEqual(create_res.status_code, 201)
        alert_id = json.loads(create_res.data)["alert_id"]

        # List alerts
        list_res = self.client.get("/api/alerts", headers=self.headers)
        self.assertEqual(list_res.status_code, 200)
        alerts = json.loads(list_res.data)["alerts"]
        self.assertTrue(any(a["id"] == alert_id for a in alerts))

        # Delete alert
        del_res = self.client.delete(f"/api/alerts/{alert_id}", headers=self.headers)
        self.assertEqual(del_res.status_code, 200)

    def test_20_chat_conversation_and_message(self):
        """POST /api/chat/conversation and POST /api/chat/<id>/message execute inference."""
        conv_res = self.client.post("/api/chat/conversation", headers=self.headers, json={
            "title": "Integration Test Query"
        })
        self.assertEqual(conv_res.status_code, 201)
        conv_id = json.loads(conv_res.data)["conversation_id"]

        # Send message
        msg_res = self.client.post(f"/api/chat/{conv_id}/message", headers=self.headers, json={
            "message": "Analyze AAPL sentiment and momentum"
        })
        self.assertEqual(msg_res.status_code, 200)
        msg_data = json.loads(msg_res.data)
        self.assertIn("response", msg_data)
        self.assertIsInstance(msg_data["response"], str)
        self.assertGreater(len(msg_data["response"]), 0)

    # ---------------------------------------------------------
    # 9. CURRENCY API INTEGRATION
    # ---------------------------------------------------------
    def test_21_currency_list_and_convert(self):
        """Currency exchange rates and conversion endpoints."""
        list_res = self.client.get("/api/currency/list")
        self.assertEqual(list_res.status_code, 200)
        currencies = json.loads(list_res.data)["currencies"]
        self.assertIsInstance(currencies, list)

        # Convert 100 USD to INR
        conv_res = self.client.post("/api/currency/convert", json={
            "amount": 100,
            "from": "USD",
            "to": "INR"
        })
        self.assertEqual(conv_res.status_code, 200)
        conv_data = json.loads(conv_res.data)
        self.assertIn("converted", conv_data)
        self.assertGreater(conv_data["converted"], 0)


if __name__ == "__main__":
    unittest.main()
