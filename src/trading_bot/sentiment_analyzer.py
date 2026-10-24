from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yfinance as yf
from trading_bot import config

class SentimentEngine:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.last_score = 0.0
        
    def fetch_news(self, ticker=config.TICKER):
        """
        Fetches latest news titles for the ticker using yfinance.
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            news = ticker_obj.news
            titles = [n['title'] for n in news] if news else []
            return titles
        except Exception as e:
            print(f"News Fetch Error: {e}")
            return []

    def analyze_sentiment(self):
        """
        Fetches news and calculates average compound score.
        Returns: Score between -1.0 (Negative) and 1.0 (Positive).
        """
        titles = self.fetch_news()
        if not titles:
            return 0.0 # Neutral if no news
            
        scores = []
        for title in titles:
            vs = self.analyzer.polarity_scores(title)
            scores.append(vs['compound'])
            
        if scores:
            self.last_score = sum(scores) / len(scores)
        else:
            self.last_score = 0.0
            
        return self.last_score

    def is_safe_to_trade(self, direction="LONG"):
        """
        Returns False if Sentiment contradicts direction strongly.
        """
        score = self.analyze_sentiment()
        
        # Filter Logic:
        # If Score is Very Negative (<-0.5), DON'T BUY.
        # If Score is Very Positive (>0.5), DON'T SHORT (not implemented yet, but good practice).
        
        print(f"📰 News Sentiment: {score:.2f}")
        
        if direction == "LONG" and score < -0.5:
             print("⛔ TRADE BLOCKED: Negative News Sentiment.")
             return False
             
        return True
