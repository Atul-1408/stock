from google import genai
import os
from datetime import datetime, timezone
import json
import re
from config import Config

class TradingChatbot:
    def __init__(self):
        # Initialize Gemini API (FREE)
        api_key = Config.GEMINI_API_KEY
            
        # Use the newer google-genai Client pattern
        try:
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set.")
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-flash-latest'
        except Exception as e:
            print(f"Gemini Init Error: {e}")
            self.client = None
        
    def get_response(self, user_id, user_message, conversation_history=[]):
        """
        Get AI response with trading context
        """
        # Get user context
        user_context = self._get_user_context(user_id)
        
        # Build system prompt with user context
        system_prompt = self._build_system_prompt(user_context)
        
        # Build conversation for Gemini
        # Gemini Client expects a list of content parts or a simple string
        full_content = f"{system_prompt}\n\n"
        
        # Add history (last 5 messages for context)
        if conversation_history:
            full_content += "Conversation History:\n"
            for msg in conversation_history[-5:]:
                role = "User" if msg['role'] == 'user' else "Assistant"
                full_content += f"{role}: {msg['content']}\n"
        
        full_content += f"\nUser: {user_message}\nAssistant:"
        
        try:
            if not self.client:
                 raise Exception("Gemini Client not initialized")

            # Call Gemini API using new Client pattern
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_content
            )
            
            # Check for response and safely extract text
            if not response or not response.text:
                raise Exception("Empty response from AI")
                
            assistant_message = response.text
            
            # Extract mentioned stocks and actions
            stocks_mentioned = self._extract_tickers(assistant_message)
            suggested_actions = self._extract_actions(assistant_message)
            
            return {
                'response': assistant_message,
                'actions': suggested_actions,
                'stocks_mentioned': stocks_mentioned
            }
        
        except Exception as e:
            print(f"Chatbot error: {e}")
            # Fallback Analysis (Degraded Mode) - Made Polite
            fallback_holdings = user_context.get('holdings', [])
            holdings_str = ', '.join(fallback_holdings) if fallback_holdings else 'the market'
            
            return {
                'response': f"I'm very sorry, but I'm having a little trouble connecting to my brain right now. Based on your portfolio in {holdings_str}, I would recommend being a bit cautious. (Technical note: {str(e)}). Could you please check the Alerts tab for sentiment signals in the meantime? I'll be here if you need anything else!",
                'actions': [{'type': 'hold', 'confidence': 'medium'}],
                'stocks_mentioned': self._extract_tickers(user_message)
            }
    
    def _build_system_prompt(self, user_context):
        """Build system prompt with user context"""
        
        # Safe extraction with defaults
        p_val = user_context.get('portfolio_value', 0)
        cash = user_context.get('cash_balance', 100000)
        pnl = user_context.get('total_pnl', 0)
        pnl_pct = user_context.get('total_pnl_pct', 0)
        win_rate = user_context.get('win_rate', 0)
        holdings = user_context.get('holdings', [])
        holdings_str = ', '.join(holdings) if holdings else 'None'
        
        return f"""You are a helpful, polite, and friendly AI trading assistant for Stock Sense. 
Your goal is to provide excellent service and assist users with their trading decisions while maintaining a warm and professional demeanor.

PERSONALITY GUIDELINES:
- **Be extremely polite and friendly.** Use greetings (e.g., "Hello!", "How can I help you today?") and polite closings.
- Use phrases like "Please," "Thank you," "I'd be happy to help," and "I'm sorry" where appropriate.
- Maintain a supportive and encouraging tone.
- If a user loses money, be empathetic but professional.

CURRENT USER CONTEXT:
- Portfolio Value: ${p_val:,.2f}
- Available Cash: ${cash:,.2f}
- Total P&L: ${pnl:,.2f} ({pnl_pct:.2f}%)
- Win Rate: {win_rate:.1f}%
- Current Holdings: {holdings_str}

CAPABILITIES:
1. Analyze stock sentiment (FinBERT scores)
2. Provide Buy/Sell/Hold recommendations
3. Risk assessments (1-10 scale)
4. Portfolio diversification advice

GUIDELINES:
- Be concise and polite.
- Use bullet points for readability.
- Check sentiment before recommending a buy.
- Warn about negative sentiment spikes kindly.
- Never guarantee profits.

Current date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"""
    
    def _get_user_context(self, user_id):
        """Get user's portfolio context"""
        try:
            from analytics_engine import calculate_portfolio_performance
            from trading_engine import get_user_portfolio, get_user_balance
            
            # Robustify with empty defaults
            metrics = calculate_portfolio_performance(user_id) or {}
            portfolio = get_user_portfolio(user_id) or []
            holdings = [h.get('ticker', 'UNKNOWN') for h in portfolio]
            cash = get_user_balance(user_id) or 0
            
            return {
                'portfolio_value': metrics.get('total_value', 0),
                'cash_balance': cash,
                'total_pnl': metrics.get('total_pnl', 0),
                'total_pnl_pct': metrics.get('total_pnl_pct', 0),
                'win_rate': metrics.get('win_rate', 0),
                'holdings': holdings
            }
        except Exception as e:
            print(f"Context fetch error: {e}")
            return {
                'portfolio_value': 0, 'cash_balance': 100000, 
                'total_pnl': 0, 'total_pnl_pct': 0, 
                'win_rate': 0, 'holdings': []
            }
    
    def _extract_tickers(self, text):
        """Extract stock tickers mentioned in response"""
        if not text: return []
        pattern = r'\b[A-Z]{2,5}\b'
        tickers = re.findall(pattern, text)
        common_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'STOP', 'BUY', 'SELL', 'HOLD', 'OK', 'AI', 'BY', 'IN', 'OF', 'OR', 'IS', 'AM', 'MY', 'AS', 'AT'}
        valid_tickers = [t for t in tickers if t not in common_words]
        return list(set(valid_tickers))
    
    def _extract_actions(self, text):
        """Extract suggested actions from response"""
        if not text: return []
        actions = []
        low_text = text.lower()
        if 'recommend buying' in low_text or 'would buy' in low_text or 'buy signal' in low_text:
            actions.append({'type': 'buy', 'confidence': 'high'})
        elif 'consider buying' in low_text or 'looking at buying' in low_text:
            actions.append({'type': 'buy', 'confidence': 'medium'})
        
        if 'recommend selling' in low_text or 'would sell' in low_text or 'sell signal' in low_text:
            actions.append({'type': 'sell', 'confidence': 'high'})
        elif 'consider selling' in low_text or 'looking at selling' in low_text:
            actions.append({'type': 'sell', 'confidence': 'medium'})
        
        if 'hold' in low_text or 'wait' in low_text:
            actions.append({'type': 'hold', 'confidence': 'medium'})
        return actions

    def analyze_stock_for_chat(self, ticker):
        """Formatted analysis for a specific ticker"""
        from sentiment_service import get_sentiment
        from trading_engine import get_current_price
        
        try:
            sentiment = get_sentiment(ticker)
            price = get_current_price(ticker)
            price_str = f"${price:.2f}"
            
            analysis = f"""
### {ticker} Intelligence Report

- **Sentiment:** {sentiment['label'].upper()} (Score: {sentiment['score']:.2f})
- **Price:** {price_str}
- **Risk Level:** {'Low' if abs(sentiment['score']) > 0.5 else 'Medium' if abs(sentiment['score']) > 0.2 else 'High'}

**AI Insight:** The current sentiment suggests a {'bullish' if sentiment['score'] > 0 else 'bearish'} trend. Monitor for news spikes.
"""
            return analysis
        except Exception as e:
            return f"\nI'm so sorry, but I couldn't fetch the analysis for {ticker} at this moment. ({str(e)})\n"

# Lazy singleton — initialized on first use, not at import time.
_chatbot = None

def get_chatbot():
    global _chatbot
    if _chatbot is None:
        _chatbot = TradingChatbot()
    return _chatbot

# Keep backwards-compat name as a proxy
class _ChatbotProxy:
    def __getattr__(self, name):
        return getattr(get_chatbot(), name)

chatbot = _ChatbotProxy()
