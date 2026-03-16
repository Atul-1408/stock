from trading_bot import config
from trading_bot.risk_manager import Trade

class PaperExchange:
    def __init__(self, initial_capital=config.INITIAL_CAPITAL):
        self.balance = initial_capital
        self.positions = [] # List of Trade objects
        self.trade_history = []
        self.commissions_paid = 0.0
        self.FEE_RATE = 0.001 # 0.1%
        self.market_data = {'price': 0.0, 'adx': 0.0} # Shared state for Telegram
        
    def get_balance(self):
        return self.balance
        
    def execute_order(self, symbol, side, qty, price, stop_loss, analysis_data):
        """
        Executes a simulated market order.
        """
        cost = qty * price
        fee = cost * self.FEE_RATE
        
        # Deduct cost + fee
        # For simulation simplicity, we deduct 'Margin' (Cost) from balance?
        # Standard: Balance = Cash. Position = Asset.
        # Buying reduces Cash.
        self.balance -= (cost + fee)
        self.commissions_paid += fee
        
        # Create Trade Record
        new_trade = Trade(symbol, side, price, stop_loss, qty, analysis_data)
        self.positions.append(new_trade)
        
        return new_trade
        
    def close_position(self, trade_index, price, reason="Exit"):
        """
        Closes a position and settles PnL + Return of Capital.
        """
        if trade_index >= len(self.positions): return
        
        trade = self.positions[trade_index]
        qty = trade.quantity # Current remaining quantity
        
        # Sell/Cover logic
        revenue = qty * price
        fee = revenue * self.FEE_RATE
        
        self.commissions_paid += fee
        self.balance += (revenue - fee) # Add back cash
        
        # Debug PnL (including fees)
        # Entry Cost (for this chunk) = Entry Price * Qty
        # Exit Rev = Price * Qty
        gross_pnl = (price - trade.entry_price) * qty if trade.direction == "LONG" else (trade.entry_price - price) * qty
        net_pnl = gross_pnl - ( (trade.entry_price * qty * self.FEE_RATE) + fee )
        
        trade.status = "CLOSED"
        self.trade_history.append({
            'symbol': trade.symbol,
            'pnl': net_pnl,
            'reason': reason,
            'exit_price': price
        })
        
        # --- Memory Logger (Self-Training) ---
        self._log_trade_memory(trade, net_pnl)
        
        # Cleanup
        self.positions.pop(trade_index)
        return net_pnl

    def _log_trade_memory(self, trade, pnl):
        """Logs trade features and outcome (1 for Win, 0 for Loss) to CSV."""
        import os
        import csv
        from datetime import datetime
        
        # Use data directory for persistence
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        filename = os.path.join(base_dir, "data", "trade_memory.csv")
        file_exists = os.path.isfile(filename)
        
        # Result: Win if PnL is positive (covering fees)
        result = 1 if pnl > 0 else 0
        
        data = trade.analysis_data
        if not data or not isinstance(data, dict):
            return # No data to log
            
        # Extract features (Matching train_brain.py and ai_validator.py)
        row = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'rsi': data.get('rsi', 50),
            'adx': data.get('adx', 25),
            'trend': data.get('trend', 1),
            'result': result
        }
        
        try:
            with open(filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            print(f"Memory Log Error: {e}")

    def modify_position(self, trade_index, action, **kwargs):
        """
        Handles partial closes or updates.
        """
        trade = self.positions[trade_index]
        if action == "PARTIAL_CLOSE":
             qty_to_close = kwargs.get('qty', 0)
             price = kwargs.get('price', 0)
             
             if qty_to_close > 0 and qty_to_close <= trade.quantity:
                 revenue = qty_to_close * price
                 fee = revenue * self.FEE_RATE
                 self.balance += (revenue - fee)
                 
                 trade.quantity -= qty_to_close
                 self.commissions_paid += fee
                 return True
        return False
