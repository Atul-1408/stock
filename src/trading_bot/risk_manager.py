from trading_bot import config

class RiskManager:
    @staticmethod
    def calculate_atr_stop(entry_price, atr_value, direction="LONG", multiplier=2.0):
        """
        Calculates the initial Stop Loss based on ATR.
        """
        if direction == "LONG":
            return entry_price - (atr_value * multiplier)
        else:
            return entry_price + (atr_value * multiplier)

    @staticmethod
    def calculate_position_size(entry_price, stop_loss, capital=config.INITIAL_CAPITAL):
        """
        Calculates position size based on Risk Per Trade (1% of Capital).
        Qty = (Capital * Risk%) / |Entry - Stop|
        """
        risk_amount = capital * config.RISK_PER_TRADE
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return 0
            
        qty = risk_amount / risk_per_share
        return int(qty)

    @staticmethod
    def check_risk_reward(entry_price, stop_loss, target_price):
        """
        Checks if the trade meets the minimum Risk:Reward ratio.
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(target_price - entry_price)
        
        if risk == 0: return False
        
        rr_ratio = reward / risk
        return rr_ratio >= config.MIN_RISK_REWARD

class Trade:
    def __init__(self, symbol, direction, entry_price, stop_loss, quantity, analysis_data):
        self.symbol = symbol
        self.direction = direction # LONG or SHORT
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.quantity = quantity
        self.initial_quantity = quantity
        self.analysis_data = analysis_data # Store the setup logic
        
        # Targets
        risk = abs(entry_price - stop_loss)
        if direction == "LONG":
            self.target_1r = entry_price + risk
            self.target_2r = entry_price + (2 * risk)
        else:
            self.target_1r = entry_price - risk
            self.target_2r = entry_price - (2 * risk)
            
        self.status = "OPEN"
        self.taken_profit = False
        self.breakeven_moved = False
        
    def update(self, current_price, current_atr=None):
        """
        Updates trade status: Checks Stops, Targets, and Trailing rules.
        Returns a list of logs/actions.
        """
        logs = []
        
        if self.status != "OPEN":
            return logs

        # 1. Check Stop Loss
        if (self.direction == "LONG" and current_price <= self.stop_loss) or \
           (self.direction == "SHORT" and current_price >= self.stop_loss):
            self.status = "STOPPED_OUT"
            logs.append(f"❌ STOP LOSS HIT at {current_price:.2f}. Trade Closed.")
            return logs

        # 2. Check Take Profit (Scale Out at 2R)
        if not self.taken_profit:
            hit_tp = (self.direction == "LONG" and current_price >= self.target_2r) or \
                     (self.direction == "SHORT" and current_price <= self.target_2r)
            if hit_tp:
                close_qty = int(self.quantity / 2)
                self.quantity -= close_qty
                self.taken_profit = True
                logs.append(f"💰 TARGET 2R HIT at {current_price:.2f}. Closed {close_qty} units. Secured Profit.")

        # 3. Breakeven Move (At 1R)
        if not self.breakeven_moved:
            if (self.direction == "LONG" and current_price >= self.target_1r) or \
               (self.direction == "SHORT" and current_price <= self.target_1r):
                self.stop_loss = self.entry_price
                self.breakeven_moved = True
                logs.append(f"🛡️ Price hit 1R. Stop moved to Breakeven ({self.stop_loss:.2f}). Risk Free.")

        # 4. Trailing Stop (Only after taking profit, or implementing a generic trail)
        # Requirement: "Let the remaining 50% ride with a Trailing Stop."
        # Use ATR trailing if ATR is provided
        if self.taken_profit and current_atr:
             # simple 2 ATR trail
            new_stop = RiskManager.calculate_atr_stop(current_price, current_atr, self.direction, multiplier=2.0)
            
            # Only move stop in favor
            if self.direction == "LONG":
                if new_stop > self.stop_loss:
                    self.stop_loss = new_stop
                    logs.append(f"📈 Trailing Stop adjusted to {self.stop_loss:.2f}")
            else:
                if new_stop < self.stop_loss:
                    self.stop_loss = new_stop
                    logs.append(f"📉 Trailing Stop adjusted to {self.stop_loss:.2f}")

        return logs
