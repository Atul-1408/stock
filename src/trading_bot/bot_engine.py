import threading
import time
from datetime import datetime, time as dt_time
import sqlite3
import yfinance as yf
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config

class TradingBotEngine:
    def __init__(self, db_path=str(Config.DB_PATH)):
        self.db_path = db_path
        self.running = False
        self.active_bots = {}  # {user_id: bot_state}

    def start(self):
        """Start the bot monitoring system"""
        self.running = True
        thread = threading.Thread(target=self._main_loop, daemon=True)
        thread.start()
        print("🤖 Trading Bot Engine Started")

    def stop(self):
        """Stop the bot system"""
        self.running = False
        print("🛑 Trading Bot Engine Stopped")

    def _main_loop(self):
        """Main bot monitoring loop - runs every 5 minutes"""
        while self.running:
            try:
                # Get all active bots
                active_users = self._get_active_bot_users()

                for user_id in active_users:
                    # Check if within trading hours
                    if not self._is_trading_hours(user_id):
                        continue

                    # Run bot cycle for this user
                    self._run_bot_cycle(user_id)

                # Wait 5 minutes before next cycle
                time.sleep(300)

            except Exception as e:
                print(f"❌ Bot Engine Error: {e}")
                time.sleep(60)

    def _run_bot_cycle(self, user_id):
        """Run one complete bot cycle for a user"""

        print(f"🔄 Running bot cycle for user {user_id}")

        # Get bot configuration
        config = self._get_bot_config(user_id)

        if not config or not config['is_active']:
            return

        # Get watchlist
        watchlist = self._get_watchlist(user_id)

        if not watchlist:
            print(f"⚠️ User {user_id} has empty watchlist")
            return

        # Check each stock
        for ticker in watchlist:
            try:
                # Generate trading signal
                signal = self._generate_signal(user_id, ticker, config)

                if signal and signal['should_trade']:
                    # Execute the trade
                    self._execute_bot_trade(user_id, signal, config)

                # Check existing positions for exit signals
                self._check_open_positions(user_id, ticker, config)

            except Exception as e:
                print(f"❌ Error processing {ticker} for user {user_id}: {e}")

    def _generate_signal(self, user_id, ticker, config) -> Optional[Dict]:
        """
        Generate trading signal combining:
        1. Sentiment analysis
        2. Technical indicators
        3. ML model prediction
        """

        print(f"📊 Analyzing {ticker}...")

        # 1. Get sentiment score
        sentiment_score = 0
        if config['use_sentiment']:
            sentiment_score = self._get_sentiment_score(ticker)

            # Skip if sentiment below threshold
            if sentiment_score < config['min_sentiment_score']:
                print(f"❌ {ticker}: Sentiment too low ({sentiment_score:.2f})")
                return None

        # 2. Get technical analysis
        technical_score = 0
        if config['use_technical']:
            technical_score = self._calculate_technical_score(ticker)

        # 3. Get ML prediction (if model exists)
        ml_score = 0
        if config['use_ml_model']:
            ml_score = self._get_ml_prediction(ticker, sentiment_score, technical_score)

        # 4. Combine scores
        weights = {
            'sentiment': 0.4 if config['use_sentiment'] else 0,
            'technical': 0.4 if config['use_technical'] else 0,
            'ml': 0.2 if config['use_ml_model'] else 0
        }

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}

        combined_score = (
            sentiment_score * weights['sentiment'] +
            technical_score * weights['technical'] +
            ml_score * weights['ml']
        )

        print(f"📈 {ticker} scores - Sentiment: {sentiment_score:.2f}, Technical: {technical_score:.2f}, ML: {ml_score:.2f}, Combined: {combined_score:.2f}")

        # 5. Generate signal based on combined score
        if combined_score >= 0.7:  # Strong BUY signal
            return self._create_buy_signal(
                ticker, combined_score, sentiment_score,
                technical_score, ml_score, config
            )

        elif combined_score <= -0.7:  # Strong SELL signal
            return self._create_sell_signal(
                ticker, combined_score, sentiment_score,
                technical_score, ml_score, config
            )

        else:
            return None  # No clear signal

    def _get_sentiment_score(self, ticker: str) -> float:
        """Get sentiment score from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get latest sentiment for this ticker
            result = cursor.execute("""
                SELECT AVG(s.sentiment_score) as avg_sentiment
                FROM sentiments s
                JOIN articles a ON s.article_id = a.id
                WHERE a.ticker = ?
                AND a.fetched_at > datetime('now', '-1 day')
            """, (ticker,)).fetchone()

            conn.close()

            if result and result['avg_sentiment']:
                # Normalize to -1 to 1 scale
                return min(1.0, max(-1.0, result['avg_sentiment']))
            return 0

        except Exception as e:
            print(f"Error getting sentiment for {ticker}: {e}")
            return 0

    def _calculate_technical_score(self, ticker: str) -> float:
        """Calculate technical score using indicators"""
        try:
            # Get historical data
            stock = yf.Ticker(ticker)
            data = stock.history(period='3mo', interval='1d')

            if data.empty or len(data) < 50:
                return 0

            # Calculate indicators
            rsi = self._calculate_rsi(data['Close'], period=14)
            rsi_score = self._normalize_rsi(rsi)

            ma_score = self._calculate_ma_score(data)
            volume_score = self._calculate_volume_score(data)
            macd_score = self._calculate_macd_score(data)

            # Combine technical scores
            technical_score = (
                rsi_score * 0.3 +
                ma_score * 0.3 +
                volume_score * 0.2 +
                macd_score * 0.2
            )

            return technical_score

        except Exception as e:
            print(f"Error calculating technical score: {e}")
            return 0

    def _calculate_rsi(self, prices, period=14) -> float:
        """Calculate RSI"""
        try:
            deltas = prices.diff()
            gain = deltas.where(deltas > 0, 0).rolling(window=period).mean()
            loss = -deltas.where(deltas < 0, 0).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return rsi.iloc[-1] if not rsi.empty else 50
        except:
            return 50

    def _normalize_rsi(self, rsi: float) -> float:
        """Convert RSI to -1 to 1 score"""
        if rsi < 30:
            return (30 - rsi) / 30  # Oversold = positive score
        elif rsi > 70:
            return -(rsi - 70) / 30  # Overbought = negative score
        else:
            return 0  # Neutral

    def _calculate_ma_score(self, data) -> float:
        """Moving average crossover score"""
        try:
            if len(data) < 50:
                return 0

            ma_20 = data['Close'].rolling(window=20).mean()
            ma_50 = data['Close'].rolling(window=50).mean()

            current_price = data['Close'].iloc[-1]
            ma_20_val = ma_20.iloc[-1]
            ma_50_val = ma_50.iloc[-1]

            if current_price > ma_20_val > ma_50_val:
                return 1.0  # Bullish
            elif current_price < ma_20_val < ma_50_val:
                return -1.0  # Bearish
            else:
                return 0.0  # Neutral
        except:
            return 0

    def _calculate_volume_score(self, data) -> float:
        """Volume analysis score"""
        try:
            if len(data) < 20:
                return 0

            avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = data['Volume'].iloc[-1]

            if current_volume > avg_volume * 1.5:
                return 0.5
            else:
                return 0
        except:
            return 0

    def _calculate_macd_score(self, data) -> float:
        """MACD score"""
        try:
            if len(data) < 26:
                return 0

            ema_12 = data['Close'].ewm(span=12).mean()
            ema_26 = data['Close'].ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()

            macd_val = macd.iloc[-1]
            signal_val = signal.iloc[-1]

            if macd_val > signal_val:
                return 0.5
            elif macd_val < signal_val:
                return -0.5
            else:
                return 0
        except:
            return 0

    def _get_ml_prediction(self, ticker: str, sentiment_score: float, technical_score: float) -> float:
        """Get ML model prediction"""
        # TODO: Implement actual ML model
        # For now, return weighted average
        return (sentiment_score + technical_score) / 2

    def _create_buy_signal(self, ticker: str, confidence: float, sentiment: float, technical: float, ml: float, config: Dict) -> Dict:
        """Create BUY signal"""

        price = self._get_current_price(ticker)

        if not price:
            return None

        position_size = self._calculate_position_size(
            price, config['max_position_size'], config['risk_level']
        )

        return {
            'should_trade': True,
            'ticker': ticker,
            'action': 'BUY',
            'confidence': confidence,
            'sentiment_score': sentiment,
            'technical_score': technical,
            'ml_score': ml,
            'price': price,
            'shares': position_size,
            'stop_loss': price * (1 - config['stop_loss_pct']),
            'take_profit': price * (1 + config['take_profit_pct']),
            'reasoning': f"Strong BUY signal (Confidence: {confidence:.2f}). Sentiment: {sentiment:.2f}, Technical: {technical:.2f}"
        }

    def _create_sell_signal(self, ticker: str, confidence: float, sentiment: float, technical: float, ml: float, config: Dict) -> Dict:
        """Create SELL signal"""

        price = self._get_current_price(ticker)

        if not price:
            return None

        return {
            'should_trade': True,
            'ticker': ticker,
            'action': 'SELL',
            'confidence': abs(confidence),
            'sentiment_score': sentiment,
            'technical_score': technical,
            'ml_score': ml,
            'price': price,
            'reasoning': f"Strong SELL signal (Confidence: {abs(confidence):.2f}). Sentiment: {sentiment:.2f}, Technical: {technical:.2f}"
        }

    def _execute_bot_trade(self, user_id: int, signal: Dict, config: Dict) -> None:
        """Execute bot trade"""

        print(f"🚀 Executing {signal['action']} for {signal['ticker']}")

        # Check if max trades per day reached
        if self._has_reached_daily_limit(user_id, config['max_trades_per_day']):
            print(f"⚠️ Daily trade limit reached for user {user_id}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Log bot trade
        cursor.execute("""
            INSERT INTO bot_trades
            (user_id, ticker, action, shares, entry_price, stop_loss, take_profit,
             sentiment_at_entry, technical_score, ml_score, status, entry_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
        """, (
            user_id, signal['ticker'], signal['action'],
            signal.get('shares', 1), signal['price'],
            signal.get('stop_loss'), signal.get('take_profit'),
            signal['sentiment_score'], signal['technical_score'],
            signal['ml_score'], now
        ))

        # Save signal
        cursor.execute("""
            INSERT INTO bot_signals
            (user_id, ticker, signal_type, confidence, sentiment_score,
             technical_score, ml_score, price, reasoning, was_executed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
        """, (
            user_id, signal['ticker'], signal['action'], signal['confidence'],
            signal['sentiment_score'], signal['technical_score'],
            signal['ml_score'], signal['price'], signal['reasoning'], now
        ))

        conn.commit()
        conn.close()

        print(f"✅ Bot trade executed: {signal['action']} {signal['ticker']}")

    def _check_open_positions(self, user_id: int, ticker: str, config: Dict) -> None:
        """Check open positions for stop loss / take profit"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        positions = cursor.execute("""
            SELECT * FROM bot_trades
            WHERE user_id = ? AND ticker = ? AND status = 'OPEN'
        """, (user_id, ticker)).fetchall()

        current_price = self._get_current_price(ticker)

        if not current_price:
            conn.close()
            return

        for position in positions:
            exit_reason = None

            if position['stop_loss'] and current_price <= position['stop_loss']:
                exit_reason = 'STOP_LOSS'

            elif position['take_profit'] and current_price >= position['take_profit']:
                exit_reason = 'TAKE_PROFIT'

            if exit_reason:
                self._close_bot_position(user_id, position, current_price, exit_reason, conn)

        conn.close()

    def _close_bot_position(self, user_id: int, position, exit_price: float, exit_reason: str, conn: sqlite3.Connection) -> None:
        """Close an open bot position"""

        print(f"🔚 Closing position: {position['ticker']} at {exit_price} ({exit_reason})")

        # Calculate P&L
        if position['action'] == 'BUY':
            pnl = (exit_price - position['entry_price']) * position['shares']
            pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
        else:
            pnl = (position['entry_price'] - exit_price) * position['shares']
            pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE bot_trades
            SET exit_price = ?, pnl = ?, pnl_pct = ?, status = 'CLOSED',
                exit_time = ?, exit_reason = ?
            WHERE id = ?
        """, (exit_price, pnl, pnl_pct, datetime.now().isoformat(), exit_reason, position['id']))

        conn.commit()

        print(f"✅ Position closed: {exit_reason} | P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """Get current stock price"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d', interval='1m')

            if not data.empty:
                return float(data['Close'].iloc[-1])
            return None
        except:
            return None

    def _calculate_position_size(self, price: float, max_position: float, risk_level: str) -> int:
        """Calculate position size based on risk"""

        risk_multipliers = {
            'LOW': 0.5,
            'MEDIUM': 1.0,
            'HIGH': 1.5
        }

        multiplier = risk_multipliers.get(risk_level, 1.0)
        max_investment = max_position * multiplier

        shares = int(max_investment / price)
        return max(1, shares)

    def _is_trading_hours(self, user_id: int) -> bool:
        """Check if within trading hours"""

        config = self._get_bot_config(user_id)

        if not config:
            return False

        current_time = datetime.now().time()
        start_time = config['trading_hours_start']
        end_time = config['trading_hours_end']

        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, '%H:%M:%S').time()
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, '%H:%M:%S').time()

        return start_time <= current_time <= end_time

    def _has_reached_daily_limit(self, user_id: int, limit: int) -> bool:
        """Check if daily trade limit reached"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        today = datetime.now().date().isoformat()

        count = cursor.execute("""
            SELECT COUNT(*) FROM bot_trades
            WHERE user_id = ? AND DATE(entry_time) = ?
        """, (user_id, today)).fetchone()[0]

        conn.close()

        return count >= limit

    def _get_active_bot_users(self) -> List[int]:
        """Get list of users with active bots"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        users = cursor.execute("""
            SELECT user_id FROM bot_configs WHERE is_active = 1
        """).fetchall()

        conn.close()

        return [u[0] for u in users]

    def _get_bot_config(self, user_id: int) -> Optional[Dict]:
        """Get bot configuration"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        config = cursor.execute("""
            SELECT * FROM bot_configs WHERE user_id = ?
        """, (user_id,)).fetchone()

        conn.close()

        return dict(config) if config else None

    def _get_watchlist(self, user_id: int) -> List[str]:
        """Get user's bot watchlist"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        tickers = cursor.execute("""
            SELECT ticker FROM bot_watchlist WHERE user_id = ?
        """, (user_id,)).fetchall()

        conn.close()

        return [t[0] for t in tickers]


# Initialize bot engine
bot_engine = TradingBotEngine()
