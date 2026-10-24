
import sqlite3
from datetime import datetime, timezone

def create_demo_alerts():
    db_file = "c:\\Users\\Atul\\project\\stock\\data\\stock_dashboard.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    
    demo_alerts = [
        ('RELIANCE.NS', 'URGENT: AI Bot has detected a massive bullish breakout in RELIANCE. Confidence: 94%.', 0.94, 1345.60),
        ('TCS.NS', 'SIGNAL: AI Engine reports a sentiment spike in TCS following positive news. Trend is bullish.', 0.85, 2596.80),
        ('GLOBAL', 'MARKET BRIEFING: AI analysis shows high liquidity across Indian indices. Sentiment is positive.', 0.72, None)
    ]
    
    for ticker, message, sentiment, price in demo_alerts:
        cursor.execute(
            """
            INSERT INTO alert_logs (alert_rule_id, user_id, ticker, alert_type, message, sentiment_score, price, triggered_at)
            VALUES (0, 0, ?, 'bot_signal', ?, ?, ?, ?)
            """,
            (ticker, message, sentiment, price, now)
        )
    
    conn.commit()
    conn.close()
    print("3 Fresh demo alerts created successfully.")

if __name__ == "__main__":
    create_demo_alerts()
