import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from datetime import datetime, timedelta, timezone
import threading
import time
import database
from trading_engine import get_current_price
from sentiment_service import get_sentiment

class AlertEngine:
    def __init__(self):
        self.running = False
        self.check_interval = 300  # Check every 5 minutes
        
    def start(self):
        """Start the alert monitoring background thread"""
        if self.running: return
        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        print("[OK] Alert Engine Started")
    
    def stop(self):
        """Stop the alert monitoring"""
        self.running = False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self.check_all_alerts()
            except Exception as e:
                print(f"Alert Engine Loop Error: {e}")
            
            time.sleep(self.check_interval)
    
    def check_all_alerts(self):
        """Check all active alert rules"""
        active_alerts = database.get_all_active_alerts()
        
        for alert in active_alerts:
            try:
                self.check_alert(alert)
            except Exception as e:
                print(f"Error checking alert {alert['id']}: {e}")
    
    def check_alert(self, alert):
        """Check if a specific alert condition is met"""
        ticker = alert['ticker']
        alert_type = alert['alert_type']
        user_id = alert['user_id']
        
        # Prevent spam - cooldown 1 hour
        if alert.get('last_triggered'):
            try:
                last_t = datetime.fromisoformat(alert['last_triggered'].replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - last_t) < timedelta(hours=1):
                    return
            except: pass
        
        triggered = False
        message = ""
        current_sentiment = None
        current_price = None
        
        if alert_type == 'sentiment_drop':
            # Use average score from last 30 days
            from database import get_sentiments_last_30_days
            rows = get_sentiments_last_30_days(ticker)
            if rows:
                current_sentiment = sum(r['sentiment_score'] for r in rows) / len(rows)
                if current_sentiment <= alert['threshold_value']:
                    triggered = True
                    message = f"[-] ALERT: {ticker} sentiment dropped to {current_sentiment:.2f}"
            
        elif alert_type == 'sentiment_rise':
            from database import get_sentiments_last_30_days
            rows = get_sentiments_last_30_days(ticker)
            if rows:
                current_sentiment = sum(r['sentiment_score'] for r in rows) / len(rows)
                if current_sentiment >= alert['threshold_value']:
                    triggered = True
                    message = f"[+] ALERT: {ticker} sentiment rose to {current_sentiment:.2f}"
        
        elif alert_type == 'price_target':
            current_price = get_current_price(ticker)
            operator = alert['condition_operator']
            threshold = alert['threshold_value']
            
            if operator == 'above' and current_price >= threshold:
                triggered = True
                message = f"[^] ALERT: {ticker} price reached ${current_price:.2f}"
            elif (operator == 'below' or operator == 'under') and current_price <= threshold:
                triggered = True
                message = f"[v] ALERT: {ticker} price dropped to ${current_price:.2f}"
        
        if triggered:
            notification_method = alert['notification_method']
            
            # Send notification (simplified for now)
            self.send_notification(user_id, notification_method, message, ticker)
            
            # Log the alert
            database.add_alert_log(
                alert_rule_id=alert['id'],
                user_id=user_id,
                ticker=ticker,
                alert_type=alert_type,
                message=message,
                sentiment=current_sentiment,
                price=current_price
            )
            
            # Update last_triggered timestamp
            database.update_alert_triggered(alert['id'])
    
    def send_notification(self, user_id, method, message, ticker):
        user = database.get_user_by_id(user_id)
        if not user: return
        
        if method in ['email', 'both']:
            print(f"[EMAIL] Mock Email to {user['email']}: {message}")
            # Real SMTP logic would go here
        
        if method in ['telegram', 'both'] and user.get('twitter_handle'): # Reusing a field or assuming telegram_id exists
            # For this demo, we'll just log it
            print(f"[SMS] Mock Telegram to user {user_id}: {message}")

# Singleton instance
alert_engine = AlertEngine()
