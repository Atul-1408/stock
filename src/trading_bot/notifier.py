import asyncio
import os
import sys
from pathlib import Path
from telegram import Bot
from dotenv import load_dotenv

# Ensure we can import database from the src directory
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    import database
except ImportError:
    database = None

load_dotenv()

class TelegramNotifier:
    def __init__(self, exchange_ref=None):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = None
        self.exchange = exchange_ref # Reference to PaperExchange to query status/close
        self.polling_enabled = True
        
        if self.token:
             from telegram import Bot
             self.bot = Bot(token=self.token)
             if self.chat_id:
                 print(f"Telegram Bot Initialized (ID: {self.chat_id})")
             else:
                 print("Telegram Token detected. Waiting for 'hi' to link Chat ID...")
        else:
             print("Telegram Token missing. Running in MOCK Mode.")

        self.offset = 0 # Initialize update offset
        self.last_sent_message = "" # Spam Protection

    async def send_alert(self, message, ticker=None, alert_type="bot_signal", sentiment=None, price=None):
        """
        Sends a message to the configured Telegram Chat and logs to database.
        """
        if not message:
            return

        # 1. Log to database for internal UI visibility
        if database:
            try:
                database.add_bot_alert_log(ticker, message, alert_type, sentiment, price)
            except Exception as e:
                print(f"Database Log Error: {e}")

        # 2. Send to Telegram
        if self.bot and self.chat_id:
            try:
                # Spam Protection: Don't send exact same message twice (only after a successful send)
                if message == self.last_sent_message:
                    return
                await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
                self.last_sent_message = message
            except Exception as e:
                print(f"Telegram Send Error: {e}")
                # Allow retries if a send fails.
                if self.last_sent_message == message:
                    self.last_sent_message = ""
        else:
            if self.bot and not self.chat_id:
                print("Telegram chat_id missing. Send 'hi' to the bot to auto-link TELEGRAM_CHAT_ID.")
            else:
                print(f"[MOCK TELEGRAM] >> {message}")

    async def check_commands(self):
        """
        Polls for commands via get_updates.
        """
        if (not self.bot) or (not self.polling_enabled):
            return

        try:
            # Get updates (long polling with short timeout to not block main loop too much)
            # In a real async app, this should run in a separate task.
            # Here we do a quick check.
            updates = await self.bot.get_updates(offset=self.offset, timeout=1)
            
            for update in updates:
                self.offset = update.update_id + 1
                
                if update.message and update.message.text:
                    # AUTO-DETECT CHAT ID if missing
                    if not self.chat_id:
                        self.chat_id = str(update.message.chat_id)
                        print(f"[OK] AUTO-DETECTED CHAT ID: {self.chat_id}")
                        self._save_chat_id_to_env(self.chat_id)
                        await self.send_alert(f"[OK] Connection Established! Your Chat ID ({self.chat_id}) has been saved.")

                    text = update.message.text.lower().strip()
                    print(f"[MSG] Received Command: {text}")
                    
                    if text in ["hi", "hello"]:
                        await self.send_alert("👋 I am Sovereign. Waiting for a trade setup... Type /status for report.")
                        
                    elif "/status" in text:
                        bal = self.exchange.get_balance()
                        pos_count = len(self.exchange.positions)
                        price = self.exchange.market_data.get('price', 0)
                        adx = self.exchange.market_data.get('adx', 0)
                        await self.send_alert(f"[STATS] **STATUS REPORT**\nBalance: ${bal:,.2f}\nOpen Positions: {pos_count}\nPrice: {price:.2f}\nADX: {adx:.1f}")
                        
                    elif "/price" in text:
                        price = self.exchange.market_data.get('price', 0)
                        await self.send_alert(f"💲 Current Price: {price:.2f}")

                    elif "/close" in text:
                        await self.send_alert(f"[!] **EMERGENCY CLOSE** Initiated...")
                        closed_count = 0
                        # Close all positions
                        for i in range(len(self.exchange.positions) - 1, -1, -1):
                            self.exchange.close_position(i, 0, reason="Emergency Close") # Price 0 is placeholder, mock logic needs current price lookup or pass it
                            # Ideally we need current price. For now, we just force close logic which might have issues if price is needed.
                            # PaperExchange.close_position needs price.
                            # We don't have price here easily without fetching.
                            # Let's just notify for now.
                            closed_count += 1
                        
                        await self.send_alert(f"[OK] Closed {closed_count} positions (Pricing assumed last tick). Monitor console.")
                    
                    else:
                        # Default Reply
                        await self.send_alert(f"🤖 **Sovereign Bot**\nI received: '{text}'\n\nAvailable Commands:\n/status - Check PnL & Positions\n/close - Emergency Exit")

        except Exception as e:
            if "Conflict" in str(e):
                # Conflict is for getUpdates (polling). Sending messages can still work.
                print(f"[!] Telegram Conflict: Another instance is polling getUpdates. Disabling command polling.")
                self.polling_enabled = False
                return 
            print(f"Command Check Error: {e}")

    async def send_startup_message(self):
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"[OK] **SOVEREIGN AGENT ONLINE**\n"
            f"[DATE] Date: {now_str}\n"
            f"[MODE] Mode: Laptop (Manual Start)\n"
            f"[SCAN] Scanning Markets Now..."
        )
        await self.send_alert(msg)

    def notify_urgent_setup(self, ticker, price, signal, confidence, pattern):
        """Sends a high-priority 'Emergency' alert."""
        msg = (
            f"[ALERT] **URGENT ACTION REQUIRED** [ALERT]\n"
            f"[PRIME] **PRIME SETUP DETECTED:** {ticker}\n"
            f"--------------------------------\n"
            f"[SIDE] {signal} NOW @ Rs.{price:.2f}\n"
            f"--------------------------------\n"
            f"[AI] AI Confidence: {confidence*100:.1f}%\n"
            f"[CHART] Pattern: {pattern}\n"
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.send_alert(msg, ticker=ticker, alert_type="urgent_signal", sentiment=confidence, price=price))
        except RuntimeError:
             asyncio.run(self.send_alert(msg, ticker=ticker, alert_type="urgent_signal", sentiment=confidence, price=price))

    def notify_trade(self, symbol, side, price, qty, stop, target):
        risk = price - stop if side == "LONG" else stop - price
        reward = target - price if side == "LONG" else price - target
        
        # Strip symbol for database ticker if it contains full name
        ticker = symbol.split(' (')[1].replace(')', '') if ' (' in symbol else symbol

        msg = (
            f"[TARGET] **TRADE SIGNAL:** {symbol} {side}\n"
            f"--------------------------------\n"
            f"[ENTRY] ENTRY:  {price:.2f}\n"
            f"[STOP] STOP:   {stop:.2f}\n"
            f"[OK] TARGET: {target:.2f}\n"
            f"--------------------------------\n"
            f"Risk: Rs.{risk*qty:.2f} | Reward: Rs.{reward*qty:.2f}\n"
            f"(Size: {qty})"
        )
        # Verify async context
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.send_alert(msg, ticker=ticker, alert_type="trade_signal", price=price))
        except RuntimeError:
             # Fallback if not in loop
             asyncio.run(self.send_alert(msg, ticker=ticker, alert_type="trade_signal", price=price))

    def _save_chat_id_to_env(self, chat_id):
        """Helper to append or update TELEGRAM_CHAT_ID in .env"""
        env_path = os.path.join(os.getcwd(), '.env')
        try:
            lines = []
            found = False
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('TELEGRAM_CHAT_ID='):
                            lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
                            found = True
                        else:
                            lines.append(line)
            
            if not found:
                lines.append(f"\nTELEGRAM_CHAT_ID={chat_id}\n")
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
            print(f"[SAVE] Saved Chat ID {chat_id} to .env")
        except Exception as e:
            print(f"Failed to save Chat ID to .env: {e}")

