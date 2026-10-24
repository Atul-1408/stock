import time
import schedule
import asyncio
from datetime import datetime, timedelta, time as dt_time
from colorama import init, Fore, Style, Back
import winsound
import config
import socket
import sys
from pathlib import Path

# Force IPv4 to fix "getaddrinfo failed" errors on some Windows setups
def force_ipv4_socket_patch():
    old_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(*args, **kwargs):
        # args[0] is hostname
        host = args[0] if args else None
        
        # Only apply patch for Yahoo Finance domains which are failing
        if host and isinstance(host, str) and 'yahoo' in host.lower():
             # Filter out IPv6 (AF_INET6)
             # Check if family is specified, if so, override to AF_INET if it was AF_UNSPEC
            if 'family' in kwargs:
                 if kwargs['family'] == socket.AF_UNSPEC:
                     kwargs['family'] = socket.AF_INET
            elif len(args) > 1 and args[1] == socket.AF_UNSPEC:
                 # args is (host, port, family, type, proto, flags)
                 lst = list(args)
                 lst[1] = socket.AF_INET
                 args = tuple(lst)
                 
            try:
                responses = old_getaddrinfo(*args, **kwargs)
                # Filter specifically for AF_INET
                return [response for response in responses if response[0] == socket.AF_INET]
            except Exception as e:
                # print(f"IPv4 Patch Error for {args}: {e}")
                raise e
        
        # For everything else (like Telegram), use default behavior
        return old_getaddrinfo(*args, **kwargs)

    socket.getaddrinfo = new_getaddrinfo

force_ipv4_socket_patch()

# Add parent directory to path to allow importing 'database' and other root modules
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from trading_bot import market_analyzer
from trading_bot import pattern_recognition
from trading_bot import decision_engine
from trading_bot.risk_manager import RiskManager
from trading_bot.sentiment_analyzer import SentimentEngine
from trading_bot.event_manager import EventManager
from trading_bot.notifier import TelegramNotifier
from trading_bot.paper_exchange import PaperExchange
from trading_bot import config

init()

# Global instances for API access
event_manager = None
paper_exchange = None
sentiment_engine = None
notifier = None
risk_manager = None
company_names = {}
_loop = None

def init_trading_system():
    global event_manager, paper_exchange, sentiment_engine, notifier, risk_manager, company_names, _loop
    
    print(f"{Back.BLUE}{Fore.WHITE}=== INITIALIZING SOVEREIGN ECOSYSTEM (MODULAR) ==={Style.RESET_ALL}")
    
    # Identify Watchlist
    print("[SCAN] Verifying Watchlist...")
    for t in config.WATCHLIST:
        company_names[t] = market_analyzer.validate_ticker(t)

    # Initialize Objects
    event_manager = EventManager()
    paper_exchange = PaperExchange()
    sentiment_engine = SentimentEngine()
    notifier = TelegramNotifier() 
    notifier.exchange = paper_exchange # Link for status reports
    risk_manager = RiskManager()
    
    # Global Persistent Loop for Sync Wrapper
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    
    print(f"[OK] Paper Exchange Loaded | Capital: ${paper_exchange.get_balance():,.2f}")
    return True

# ==========================================
# 2. DEFINE THE WORKER FUNCTION
# ==========================================
def wait_for_market_open():
    """NSE opens 09:15 AM, closes 15:30 PM (IST)."""
    india_now = datetime.now() # System is in IST
    current_time = india_now.time()
    day_of_week = india_now.weekday() # 0=Mon, 6=Sun

    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)

    is_weekend = day_of_week >= 5
    is_closed = (current_time > market_close) or (current_time < market_open) or is_weekend

    if is_closed:
        # Calculate target wake up time
        if current_time > market_close or is_weekend:
            # Wake up tomorrow (or Monday)
            days_ahead = 1
            if day_of_week == 4: days_ahead = 3 # Fri -> Mon
            elif day_of_week == 5: days_ahead = 2 # Sat -> Mon
            target_date = india_now.date() + timedelta(days=days_ahead)
        else:
            # Wake up today at 9:15
            target_date = india_now.date()
        
        target_wakeup = datetime.combine(target_date, market_open)
        sleep_seconds = (target_wakeup - india_now).total_seconds()
        sleep_hours = sleep_seconds / 3600

        msg = f"Market Closed. Bot sleeping until 9:15 AM (Next Trading Day)."
        print(f"{Fore.CYAN}{msg} (approx {sleep_hours:.1f} hours){Style.RESET_ALL}")
        send_async_alert(msg)
        
        # Long Sleep
        time.sleep(sleep_seconds)
        
        print(f"{Fore.GREEN}Good Morning! Market Opening...{Style.RESET_ALL}")
        send_async_alert("☀️ Bot Waking Up!")

def run_market_scan():
    """
    Synchronous wrapper for the scan logic. 
    """
    # LOCAL IMPORTS TO FORCE SCOPE RESOLUTION
    import market_analyzer
    import pattern_recognition
    import decision_engine
    
    # Explicit Globals
    global paper_exchange, notifier, event_manager
    global last_briefing_time, last_opt_time
    
    # Time
    now = datetime.now()
    scan_time = now.strftime("%H:%M:%S")
    print(f"\n{Fore.YELLOW}=== SCAN TIME: {scan_time} ==={Style.RESET_ALL}")

    # 1. Event Check
    if event_manager.check_event_impact():
        print("Active Event Horizon. Trading Paused.")
        return

    # 2. Report Aggregator
    market_report = []
    best_pick = None
    any_signal = False

    # Synchronous Loop
    for ticker in config.WATCHLIST:
        try:
            # --- Fetch ---
            df = market_analyzer.fetch_data(ticker=ticker)
            if df is None: continue

            # --- Analyze ---
            df = pattern_recognition.detect_all(df)
            current_price = df.iloc[-1]['Close']
            ema = df.iloc[-1].get(f"EMA_{config.EMA_PERIOD}", current_price)
            trend = "Bullish" if current_price > ema else "Bearish"

            # --- Decision ---
            signal_result = decision_engine.analyze_setup(df)
            short_signal = "Neutral"
            signal_name = signal_result['signal']

            # --- Sniper Mode (Emergency Signal) ---
            conf = signal_result.get('confidence', 0)
            if ("STRONG" in signal_name) and (conf >= 0.85):
                # Trigger Urgent Alert
                print(f"{Back.RED}{Fore.WHITE} URGENT SETUP: {ticker} ({signal_name}) {Style.RESET_ALL}")
                pattern_desc = signal_result.get('strategy', 'Pattern Match')
                msg_urgent = f"🚨 **URGENT SETUP**: {ticker} ({signal_name})\n💰 Price: ₹{current_price:.2f}\n🧠 Confidence: {conf*100:.0f}%\n🛠 Strategy: {pattern_desc}"
                send_async_alert(msg_urgent, ticker=ticker, alert_type="urgent_signal", sentiment=conf, price=current_price)
                notifier.notify_urgent_setup(ticker, current_price, "BUY" if "BUY" in signal_name else "SELL", conf, pattern_desc)

            if "BUY" in signal_name:
                short_signal = "🟢 BUY"
                any_signal = True
                if not best_pick: best_pick = ticker
                execute_trade(signal_result, ticker, current_price, df)
            
            elif "SELL" in signal_name:
                short_signal = "🔴 SELL"
                any_signal = True
            elif trend == "Bullish": short_signal = "⚪ Bullish"
            else: short_signal = "🔴 Bearish"

            # --- Add to Report ---
            short_name = ticker.split('.')[0][:8] 
            market_report.append({
                "name": short_name,
                "price": current_price,
                "signal": short_signal,
                "note": signal_result.get('strategy', '') if "BUY" in signal_name else ""
            })

            # --- Update Shared State ---
            current_adx = df.iloc[-1].get(f"ADX_{config.ADX_PERIOD}", 0)
            paper_exchange.market_data = {'price': current_price, 'adx': current_adx}

            # --- Manage Positions ---
            manage_positions(ticker, current_price, df)

            print(f"> {short_name}: {short_signal} | ₹{current_price:.2f}")
            time.sleep(1) 

        except Exception as e:
            print(f"Error scanning {ticker}: {e}")

    # 3. Briefing Message
    time_since_last = (now - last_briefing_time).seconds / 60
    should_send = any_signal or (time_since_last >= 15)

    if should_send and market_report:
        msg = "🇮🇳 **MARKET BRIEFING** (5 Stocks)\n"
        msg += "-----------------------------\n"
        
        for item in market_report:
            note = f"({item['note']})" if item['note'] else ""
            msg += f"**{item['name']}**: {item['signal']} (₹{item['price']:.0f}) {note}\n"
            
        msg += "-----------------------------\n"
        if best_pick:
             msg += f"⚡ **Best Pick:** {best_pick}\n"
        else:
             msg += f"⚡ **Best Pick:** None (Wait)\n"
             
        # Send via Persistent Loop
        send_async_alert(msg)
        last_briefing_time = now
        print(f"{Fore.MAGENTA}Briefing Sent.{Style.RESET_ALL}")

    print("=" * 40)

def manage_positions(ticker, current_price, df):
    current_atr = df.iloc[-1].get(f"ATR_{config.ATR_PERIOD}", 0)
    
    for i in range(len(paper_exchange.positions) - 1, -1, -1):
        trade = paper_exchange.positions[i]
        if trade.symbol != ticker or trade.status != 'OPEN':
            continue
            
        logs = trade.update(current_price, current_atr)
        for log in logs:
            print(log)
            if "TARGET 2R" in log:
                 paper_exchange.modify_position(i, "PARTIAL_CLOSE", qty=trade.initial_quantity//2, price=current_price)
                 send_async_alert(f"💰 {ticker} Profit Taken at {current_price:.2f}")
                 
        if trade.status == "STOPPED_OUT":
            pnl = paper_exchange.close_position(i, trade.stop_loss, reason="Stop Loss")
            print(f"{Fore.RED}Position Closed. PnL: ${pnl:.2f}{Style.RESET_ALL}")
            send_async_alert(f"❌ {ticker} Stopped Out. PnL: ${pnl:.2f}")

def execute_trade(signal, ticker, current_price, df):
    # Sentiment Check
    # if not sentiment_engine.is_safe_to_trade("LONG"): return
    
    stop_loss = signal.get('stop_loss', current_price * 0.95)
    target = signal.get('take_profit', current_price * 1.05)
    qty = risk_manager.calculate_position_size(paper_exchange.get_balance(), current_price, stop_loss)
    
    if qty > 0:
        winsound.Beep(1000, 500)
        print(f"{Back.GREEN}{Fore.BLACK} TRADE EXECUTED {Style.RESET_ALL}")
        
        full_symbol = f"{company_names.get(ticker, ticker)} ({ticker})"
        paper_exchange.execute_order(ticker, "LONG", qty, current_price, stop_loss, result=signal)
        notifier.notify_trade(full_symbol, "LONG", current_price, qty, stop_loss, target)

# Global Persistent Loop for Sync Wrapper
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

def send_async_alert(msg, ticker=None, alert_type="bot_signal", sentiment=None, price=None):
    """Helper to run async alert using persistent loop via the notifier."""
    try:
        _loop.run_until_complete(notifier.send_alert(msg, ticker=ticker, alert_type=alert_type, sentiment=sentiment, price=price))
    except Exception as e:
        print(f"Alert Error: {e}")

def run_bot_engine():
    global last_briefing_time, last_opt_time
    
    last_briefing_time = datetime.now() - timedelta(minutes=20)
    last_opt_time = datetime.now()

    print("System Starting Loop...")
    
    # Startup Message
    send_async_alert(
        f"SOVEREIGN ONLINE (Flask Integrated)\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Mode: Background Thread"
    )
    
    # Schedule
    schedule.every(1).minutes.do(run_market_scan) # 1 Minute Cycle

    # --- Self-Learning Schedule (Sunday 10:00 AM) ---
    def run_brain_training():
        from trading_bot import train_brain
        print(f"\n{Fore.MAGENTA}WEEKLY BRAIN SURGERY INITIATED...{Style.RESET_ALL}")
        train_brain.run_brain_training()
        send_async_alert("Weekly AI Retraining Complete. Mode Updated.")

    schedule.every().sunday.at("10:00").do(run_brain_training)

    print("Loop Active...")
    while True:
        try:
            # Check Market Hours at start of loop
            wait_for_market_open()
            
            schedule.run_pending()
            
            # Poll Telegram using Persistent Loop
            try:
                _loop.run_until_complete(notifier.check_commands())
            except Exception as e:
                print(f"Telegram Error: {e}")
            
            time.sleep(1)
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    init_trading_system()
    run_bot_engine()
