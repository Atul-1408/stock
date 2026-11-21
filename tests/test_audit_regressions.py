"""Regression tests for the Nov-2026 audit fixes (crashers, authz, validation, leaks)."""
import json
import unittest

import app as flask_app
import database

app = flask_app.app


class AuditRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = False  # behave like production: 500s are returned, not raised
        app.config["PROPAGATE_EXCEPTIONS"] = False
        database.init_db()
        cls.c = app.test_client()

        def reg(email):
            r = cls.c.post("/api/auth/signup", json={"email": email, "password": "Passw0rd!!", "username": email.split("@")[0]})
            d = r.get_json()
            return d["user_id"], {"Authorization": f"Bearer {d['access_token']}"}

        cls.u1, cls.h1 = reg("audit1@example.com")
        cls.u2, cls.h2 = reg("audit2@example.com")

    # --- startup crashers ---
    def test_app_imports_without_windows_only_modules(self):
        import chatbot_engine, trading_bot.main  # noqa: F401  (would raise NameError / ModuleNotFoundError)

    # --- null / malformed JSON must be 400, never 500 ---
    def test_null_json_bodies_return_4xx(self):
        for method, url in [("put", "/api/bot/config"), ("post", "/api/bot/watchlist"), ("post", "/api/trade"),
                            ("post", "/api/profile/update"), ("post", "/api/alerts"), ("post", "/api/chat/conversation"),
                            ("post", "/api/social/share"), ("put", "/api/user/currency"), ("post", "/api/currency/convert")]:
            r = getattr(self.c, method)(url, headers=self.h1, data="null", content_type="application/json")
            self.assertLess(r.status_code, 500, f"{method.upper()} {url} -> {r.status_code}")

    # --- authorization ---
    def test_bot_clear_requires_admin(self):
        r = self.c.delete("/api/alerts/bot-clear", headers=self.h2)
        self.assertEqual(r.status_code, 403)

    def test_workers_health_requires_auth(self):
        self.assertEqual(self.c.get("/api/workers/health").status_code, 401)

    def test_health_does_not_leak_internals(self):
        body = json.dumps(self.c.get("/api/health").get_json())
        for secret in ("database_error", "environment", "last_error", "last_heartbeat"):
            self.assertNotIn(secret, body)

    # --- validation ---
    def test_profile_rejects_javascript_avatar_and_huge_bio(self):
        self.assertEqual(self.c.post("/api/profile/update", headers=self.h1, json={"avatar_url": "javascript:alert(1)"}).status_code, 400)
        self.assertEqual(self.c.post("/api/profile/update", headers=self.h1, json={"bio": "A" * 5000}).status_code, 400)

    def test_social_input_checks(self):
        self.assertEqual(self.c.post(f"/api/social/follow/{self.u1}", headers=self.h1).status_code, 400)
        self.assertEqual(self.c.post("/api/social/follow/99999", headers=self.h1).status_code, 404)
        self.assertEqual(self.c.post("/api/social/like/99999", headers=self.h1).status_code, 404)
        self.assertEqual(self.c.post("/api/social/comment/99999", headers=self.h1, json={"comment": "hi"}).status_code, 404)
        self.assertEqual(self.c.post("/api/social/comment/1", headers=self.h1, json={"comment": ""}).status_code, 400)

    def test_bot_config_rejects_nonsense(self):
        self.assertEqual(self.c.put("/api/bot/config", headers=self.h1, json={"stop_loss_pct": -5}).status_code, 400)
        self.assertEqual(self.c.put("/api/bot/config", headers=self.h1, json={"risk_level": "YOLO"}).status_code, 400)

    def test_convert_does_not_echo_exceptions(self):
        r = self.c.post("/api/currency/convert", json={"amount": "abc"})
        self.assertEqual(r.status_code, 400)
        self.assertNotIn("could not convert", json.dumps(r.get_json()))

    # --- chat delete route exists and is owner-scoped ---
    def test_chat_delete_is_owner_scoped(self):
        cid = self.c.post("/api/chat/conversation", headers=self.h1, json={"title": "t"}).get_json()["conversation_id"]
        self.assertEqual(self.c.delete(f"/api/chat/{cid}", headers=self.h2).status_code, 404)
        self.assertEqual(self.c.delete(f"/api/chat/{cid}", headers=self.h1).status_code, 200)

    # --- OTP per-email throttle (brute-force protection) ---
    def test_otp_verify_throttled_per_email(self):
        codes = [self.c.post("/api/auth/otp/verify", json={"email": "victim@example.com", "otp": f"{i:06d}"},
                             environ_overrides={"REMOTE_ADDR": f"10.0.0.{i}"}).status_code for i in range(8)]
        self.assertIn(429, codes, "OTP guesses from rotating IPs must still hit the per-email limit")

    # --- round 2 fixes ---
    def test_stock_details_requires_auth_and_valid_symbol(self):
        self.assertEqual(self.c.get("/api/stocks/AAPL/details").status_code, 401)
        self.assertEqual(self.c.get("/api/stocks/<script>/details", headers=self.h1).status_code, 400)

    def test_trade_rejects_bad_ticker_action_and_huge_quantity(self):
        for body in ({"ticker": "AA PL;", "action": "BUY", "shares": 1},
                     {"ticker": "AAPL", "action": "HACK", "shares": 1},
                     {"ticker": "AAPL", "action": "BUY", "shares": 10**9}):
            self.assertEqual(self.c.post("/api/trade", headers=self.h1, json=body).status_code, 400, body)

    def test_bot_config_ranges(self):
        for body in ({"stop_loss_pct": 5}, {"take_profit_pct": 0}, {"max_trades_per_day": 1000}):
            self.assertEqual(self.c.put("/api/bot/config", headers=self.h1, json=body).status_code, 400, body)
        self.assertEqual(self.c.put("/api/bot/config", headers=self.h1, json={"stop_loss_pct": 0.05}).status_code, 200)

    def test_otp_is_not_stored_in_plaintext(self):
        import otp_service
        from datetime import datetime, timedelta, timezone
        code = otp_service.generate_otp()
        database.save_otp("hash@example.com", code, (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat())
        with database.get_connection() as conn:
            stored = conn.execute("SELECT code FROM otp_codes WHERE email=?", ("hash@example.com",)).fetchone()["code"]
        self.assertNotEqual(stored, code)
        self.assertTrue(database.verify_otp("hash@example.com", code))
        self.assertFalse(database.verify_otp("hash@example.com", code), "OTP must be single-use")

    def test_otp_lockout_after_five_failed_attempts(self):
        import otp_service
        from datetime import datetime, timedelta, timezone
        code = otp_service.generate_otp()
        email = "lockout@example.com"
        database.save_otp(email, code, (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat())
        
        # 5 wrong guesses
        for _ in range(5):
            self.assertFalse(database.verify_otp(email, "000000"))

        # The 6th attempt with CORRECT code must fail because OTP is locked
        self.assertFalse(database.verify_otp(email, code))

    def test_otp_delete_expired_rows(self):
        from datetime import datetime, timedelta, timezone
        expired_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        database.save_otp("expired@example.com", "123456", expired_time)
        deleted = database.delete_expired_otps()
        self.assertGreaterEqual(deleted, 1)

    def test_stale_cached_price_is_not_used(self):
        import trading_engine
        from unittest import mock
        old = "2020-01-01T00:00:00+00:00"
        with mock.patch("database.get_market_data", return_value={"last_price": 100.0, "updated_at": old}), \
             mock.patch("order_validator.is_market_hours", return_value=True), \
             mock.patch("trading_engine.yf.Ticker", side_effect=RuntimeError("offline")):
            self.assertIsNone(trading_engine.get_current_price("AAPL"))

    def test_search_limit_is_clamped(self):
        r = self.c.get("/api/stocks/search?q=a&limit=-1")
        self.assertEqual(r.status_code, 200)

    def test_token_refresh_and_rotation(self):
        # Signup user and receive cookie
        signup_res = self.c.post("/api/auth/signup", json={
            "email": "refreshtest@example.com",
            "password": "Password123!",
            "username": "refreshtest"
        })
        self.assertEqual(signup_res.status_code, 201)
        self.assertIn("refresh_token", signup_res.headers.get("Set-Cookie", ""))

        # Call refresh
        refresh_res = self.c.post("/api/auth/refresh")
        self.assertEqual(refresh_res.status_code, 200)
        data = refresh_res.get_json()
        self.assertIn("access_token", data)

        # Test authenticated request with new access token
        new_headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_res = self.c.get("/api/auth/me", headers=new_headers)
        self.assertEqual(me_res.status_code, 200)

    def test_token_logout_blocklist(self):
        signup_res = self.c.post("/api/auth/signup", json={
            "email": "logoutuser@example.com",
            "password": "Password123!",
            "username": "logoutuser"
        })
        self.assertEqual(signup_res.status_code, 201)
        token = signup_res.get_json()["access_token"]
        auth_hdr = {"Authorization": f"Bearer {token}"}

        # Logout revokes token
        logout_res = self.c.post("/api/auth/logout", headers=auth_hdr)
        self.assertEqual(logout_res.status_code, 200)

        # Subsequent use of revoked token must return 401
        me_res = self.c.get("/api/auth/me", headers=auth_hdr)
        self.assertEqual(me_res.status_code, 401)

    def test_admin_role_authorization(self):
        # Default user is role 'user' and rejected
        user_res = self.c.delete("/api/alerts/bot-clear", headers=self.h2)
        self.assertEqual(user_res.status_code, 403)

        # Promote user to admin
        database.set_user_role(self.u2, "admin")
        self.assertEqual(database.get_user_role(self.u2), "admin")

        # Now admin can clear bot alerts
        admin_res = self.c.delete("/api/alerts/bot-clear", headers=self.h2)
        self.assertEqual(admin_res.status_code, 200)

        # Demote back
        database.set_user_role(self.u2, "user")

    def test_social_privacy_hides_private_user_trades(self):
        # Set user 1 as private
        with database.get_connection() as conn:
            conn.execute("UPDATE users SET is_public = 0 WHERE id = ?", (self.u1,))
            conn.commit()

        # Create shared trade for user 1
        trade_id = database.create_shared_trade(self.u1, "AAPL", "BUY", 100.0, 150.0, 0.5, "Private trade note")

        # Feed must NOT contain this trade
        feed = database.get_shared_trades_feed()
        feed_ids = [t['id'] for t in feed]
        self.assertNotIn(trade_id, feed_ids)

        # User 2 attempting to like or comment on private user's trade must receive 404
        like_res = self.c.post(f"/api/social/like/{trade_id}", headers=self.h2)
        self.assertEqual(like_res.status_code, 404)

        comment_res = self.c.post(f"/api/social/comment/{trade_id}", headers=self.h2, json={"comment": "Nice trade"})
        self.assertEqual(comment_res.status_code, 404)

        # Reset user 1 to public
        with database.get_connection() as conn:
            conn.execute("UPDATE users SET is_public = 1 WHERE id = ?", (self.u1,))
            conn.commit()


if __name__ == "__main__":
    unittest.main()
