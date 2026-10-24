from datetime import datetime, time
from trading_bot import config

class EventManager:
    def __init__(self):
        # Hardcoded Blackout Zones (e.g. Fed Announcements, volatile opens)
        # Format: (Start Time, End Time)
        self.blackout_zones = [
            (time(14, 0), time(14, 30)), # Simulated Volatile Window (e.g. Major Data Release)
        ]
        
    def check_blackout(self):
        """
        Returns True if current time is within a blackout zone.
        """
        now = datetime.now().time()
        
        for start, end in self.blackout_zones:
            if start <= now <= end:
                return True, "High Impact Event Window"
                
        # We can also add dynamic economic calendar checks here later
        return False, "Market Normal"

    def check_event_impact(self):
        """
        Checks if there is a high-impact economic event currently happening.
        Returns: True if trading should be HALTED, False if SAFE.
        """
        # For now, return False (Safe) to stop the crash.
        # In the future, we can add logic to check for specific times.
        return False
