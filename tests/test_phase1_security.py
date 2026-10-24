"""Phase 1 Security Hardening Test Suite.

Tests all required security verifications:
1. Valid login
2. Invalid login (wrong password, non-existent user, OTP user)
3. Expired token
4. Missing token
5. Invalid/tampered token
6. Unauthorized resource access (private profile, private trades, unauthenticated feeds, order limits)
7. Disallowed CORS origin
8. Allowed CORS origin
9. Rate-limit enforcement
10. Google credential verification
"""

import os
import sys
from pathlib import Path
from datetime import timedelta, datetime, timezone

# Ensure project root and src/ are in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

import unittest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

# Import app and database
from src.app import app
import src.database as database
from src.config import Config


class TestPhase1Security(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        cls.client = app.test_client()

        # Initialize clean test users in database
        database.init_db()

        # User 1: Regular user
        cls.user1_email = "sec_test_user1@example.com"
        cls.user1_password = "SecurePassword123!"
        existing_user1 = database.get_user_by_email(cls.user1_email)
        if not existing_user1:
            cls.user1_id = database.create_user(
                cls.user1_email,
                generate_password_hash(cls.user1_password),
                username="sec_user1",
                full_name="Security User One"
            )
        else:
            cls.user1_id = existing_user1['id']
            # Reset balance to known amount
            database.update_user_balance(cls.user1_id, 1000.0)

        # User 2: Private user
        cls.user2_email = "sec_test_user2_private@example.com"
        cls.user2_password = "SecurePassword456!"
        existing_user2 = database.get_user_by_email(cls.user2_email)
        if not existing_user2:
            cls.user2_id = database.create_user(
                cls.user2_email,
                generate_password_hash(cls.user2_password),
                username="sec_user2_private",
                full_name="Private User Two"
            )
        else:
            cls.user2_id = existing_user2['id']

        # Ensure user 2 is private
        database.update_user_profile(cls.user2_id, "Private bio", "", False, "")

        # User 3: OTP-only user
        cls.user3_email = "sec_test_user3_otp@example.com"
        existing_user3 = database.get_user_by_email(cls.user3_email)
        if not existing_user3:
            cls.user3_id = database.create_user(
                cls.user3_email,
                "__OTP_AUTH__",
                username="otp_user"
            )
        else:
            cls.user3_id = existing_user3['id']

    # --- 1. VALID LOGIN ---
    def test_01_valid_login(self):
        """Test legitimate login with valid credentials."""
        res = self.client.post('/api/auth/login', json={
            "email": self.user1_email,
            "password": self.user1_password
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertTrue('access_token' in data)
        self.assertEqual(data.get('user_id'), self.user1_id)

    # --- 2. INVALID LOGIN ---
    def test_02_invalid_login_wrong_password(self):
        """Test login fails with incorrect password without leaking info."""
        res = self.client.post('/api/auth/login', json={
            "email": self.user1_email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(data.get('message'), "Invalid email or password.")

    def test_03_invalid_login_nonexistent_user(self):
        """Test login fails with nonexistent user without enumeration."""
        res = self.client.post('/api/auth/login', json={
            "email": "definitely_non_existent_9999@example.com",
            "password": "SomePassword123!"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(data.get('message'), "Invalid email or password.")

    def test_04_invalid_login_otp_user(self):
        """Test OTP user cannot log in via password without crashing."""
        res = self.client.post('/api/auth/login', json={
            "email": self.user3_email,
            "password": "AnyPassword123!"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(data.get('message'), "Invalid email or password.")

    # --- 3. EXPIRED TOKEN ---
    def test_05_expired_token(self):
        """Test expired JWT token is rejected with standard 401 error."""
        with app.app_context():
            expired_token = create_access_token(
                identity=str(self.user1_id),
                expires_delta=timedelta(seconds=-10)
            )

        res = self.client.get('/api/auth/me', headers={
            "Authorization": f"Bearer {expired_token}"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('error'), 'Token Expired')

    # --- 4. MISSING TOKEN ---
    def test_06_missing_token(self):
        """Test protected endpoint without token returns 401 Unauthorized."""
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('error'), 'Unauthorized')

    # --- 5. INVALID TOKEN ---
    def test_07_invalid_token(self):
        """Test malformed/tampered token returns 401 Invalid Token."""
        res = self.client.get('/api/auth/me', headers={
            "Authorization": "Bearer this_is_a_completely_fake_and_tampered_jwt"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get('error'), 'Invalid Token')

    # --- 6. UNAUTHORIZED RESOURCE ACCESS ---
    def test_08_unauthenticated_bot_alerts(self):
        """Test /api/alerts/bot requires authentication."""
        res = self.client.get('/api/alerts/bot')
        self.assertEqual(res.status_code, 401)

    def test_09_unauthenticated_social_trades(self):
        """Test /api/social/trades requires authentication."""
        res = self.client.get('/api/social/trades')
        self.assertEqual(res.status_code, 401)

    def test_10_private_profile_access_denied(self):
        """Test user cannot access a private user's profile summary."""
        with app.app_context():
            user1_token = create_access_token(identity=str(self.user1_id))

        res = self.client.get(f'/api/profile/summary/{self.user2_id}', headers={
            "Authorization": f"Bearer {user1_token}"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data.get('message'), "This profile is private.")

    def test_11_private_user_trades_access_denied(self):
        """Test user cannot access a private user's trade feed."""
        with app.app_context():
            user1_token = create_access_token(identity=str(self.user1_id))

        res = self.client.get(f'/api/social/trades/{self.user2_id}', headers={
            "Authorization": f"Bearer {user1_token}"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data.get('message'), "This user's trades are private.")

    def test_12_order_negative_quantity_rejected(self):
        """Test order with zero or negative quantity is rejected with 400."""
        with app.app_context():
            user1_token = create_access_token(identity=str(self.user1_id))

        res = self.client.post('/api/orders', headers={
            "Authorization": f"Bearer {user1_token}"
        }, json={
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": -5,
            "price": 150.0
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Quantity must be greater than zero", data.get('message', ''))

    def test_13_order_insufficient_balance_rejected(self):
        """Test order exceeding user balance is rejected."""
        with app.app_context():
            user1_token = create_access_token(identity=str(self.user1_id))

        # User 1 balance is set to 1000.0, attempt to buy $50,000 worth of AAPL
        res = self.client.post('/api/orders', headers={
            "Authorization": f"Bearer {user1_token}"
        }, json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 250,
            "price": 200.0  # 250 * 200 = 50,000 > 1,000
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Insufficient funds", data.get('message', ''))

    def test_14_order_insufficient_shares_rejected(self):
        """Test sell order exceeding user owned shares is rejected."""
        with app.app_context():
            user1_token = create_access_token(identity=str(self.user1_id))

        # User owns 0 shares of TSLA, attempt to sell 10 shares
        res = self.client.post('/api/orders', headers={
            "Authorization": f"Bearer {user1_token}"
        }, json={
            "symbol": "TSLA",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": 250.0
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Insufficient shares", data.get('message', ''))

    # --- 7. DISALLOWED CORS ORIGIN ---
    def test_15_cors_disallowed_origin(self):
        """Test disallowed origin does not receive Access-Control-Allow-Origin header."""
        res = self.client.get('/api/ticker-tape?tickers=AAPL', headers={
            "Origin": "http://malicious-site.attacker.com"
        })
        cors_header = res.headers.get('Access-Control-Allow-Origin')
        self.assertNotEqual(cors_header, "http://malicious-site.attacker.com")
        self.assertNotEqual(cors_header, "*")

    # --- 8. ALLOWED CORS ORIGIN ---
    def test_16_cors_allowed_origin(self):
        """Test allowed frontend origin receives Access-Control-Allow-Origin header."""
        res = self.client.get('/api/ticker-tape?tickers=AAPL', headers={
            "Origin": "http://localhost:5173"
        })
        cors_header = res.headers.get('Access-Control-Allow-Origin')
        self.assertEqual(cors_header, "http://localhost:5173")

    # --- 9. RATE LIMITING ---
    def test_17_rate_limit_behavior(self):
        """Test rapid calls exceeding limit return 429 Too Many Requests."""
        # /api/auth/otp/send is limited to 5 per minute
        triggered_429 = False
        for i in range(12):
            res = self.client.post('/api/auth/otp/send', json={
                "email": f"ratelimit_probe_{i}@example.com"
            })
            if res.status_code == 429:
                triggered_429 = True
                data = res.get_json()
                self.assertEqual(data.get('error'), 'Too Many Requests')
                break

        self.assertTrue(triggered_429, "Expected 429 Too Many Requests to trigger within 12 rapid calls")

    # --- 10. GOOGLE CREDENTIAL VERIFICATION ---
    def test_18_google_missing_credential(self):
        """Test Google auth with missing credential returns 400."""
        res = self.client.post('/api/auth/google', json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get('message'), "Google credential is required.")

    def test_19_google_invalid_credential_fails_safely(self):
        """Test Google auth with forged/invalid token fails safely with 401 or 503."""
        res = self.client.post('/api/auth/google', json={
            "credential": "forged.fake.google.credential"
        })
        # If GOOGLE_CLIENT_ID is not configured, returns 503; if configured, returns 401
        self.assertIn(res.status_code, (401, 503))
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertNotIn("Traceback", data.get('message', ''))


if __name__ == '__main__':
    unittest.main()
