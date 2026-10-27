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
            self.model_name = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        except Exception as e:
            print(f"Gemini Init Error: {e}")
            self.client = None
        
    def get_response(self, user_id, user_message, conversation_history=[]):
        """
        Get AI response with trading context
        """
        # Check for unsupported questions (tax, legal, guaranteed return requests)
        unsupported_reply = self._handle_unsupported_query(user_message)
        if unsupported_reply:
            return {
                'response': unsupported_reply,
                'actions': [],
                'stocks_mentioned': self._extract_tickers(user_message)
            }

        # Get user context and grounded market data for mentioned tickers
        user_context = self._get_user_context(user_id)
        mentioned_tickers = self._extract_tickers(user_message)
        market_context = self._get_grounded_market_context(mentioned_tickers)

        # Build grounded system prompt
        system_prompt = self._build_system_prompt(user_context, market_context)
        
        # Build conversation for Gemini
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

            # Call Gemini API with automatic model fallback
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_content
                )
            except Exception:
                fallback_models = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash-lite"]
                alt_model = next((m for m in fallback_models if m != self.model_name), "gemini-flash-lite-latest")
                response = self.client.models.generate_content(
                    model=alt_model,
                    contents=full_content
                )
            
            if not response or not response.text:
                raise Exception("Empty response from AI")
                
            assistant_message = response.text
            
            # Extract mentioned stocks and actions
            stocks_mentioned = list(set(mentioned_tickers + self._extract_tickers(assistant_message)))
            suggested_actions = self._extract_actions(assistant_message)
            
            return {
                'response': assistant_message,
                'actions': suggested_actions,
                'stocks_mentioned': stocks_mentioned
            }
        
        except Exception:
            # Degraded Fallback Mode: Clean, secure, and helpful without leaking internal exception traces
            fallback_holdings = user_context.get('holdings', [])
            holdings_str = ', '.join(fallback_holdings) if fallback_holdings else 'your monitored universe'

            fallback_text = (
                f"Hello! I am currently operating in resilient offline mode. "
                f"Based on available market intelligence for {holdings_str}, maintain disciplined risk management. "
            )
            if market_context:
                fallback_text += f"\n\n**Grounded Market Feed:**\n{market_context}\n\n"
            fallback_text += (
                "Please verify active orders and signals on the Trading Desk. "
                "How else may I assist your portfolio analysis?"
            )
            
            return {
                'response': fallback_text,
                'actions': [{'type': 'hold', 'confidence': 'medium'}],
                'stocks_mentioned': mentioned_tickers
            }
    
    def _handle_unsupported_query(self, message: str) -> Optional[str]:
        """Detect and gracefully handle questions outside financial analytics scope."""
        if not message:
            return None
        low = message.lower()

        # Guaranteed profit requests
        if any(p in low for p in ["guaranteed return", "guarantee profit", "100% win", "can't lose", "risk free"]):
            return (
                "Market investments carry inherent capital risk, and no financial model or algorithm can guarantee "
                "trading profits or risk-free returns. Past sentiment trends and technical indicators are informational "
                "and should always be combined with strict position sizing and stop-loss rules."
            )

        # Tax or legal inquiries
        if any(p in low for p in ["tax advice", "file my taxes", "legal advice", "tax deduction for trades", "tax loop"]):
            return (
                "I specialize in financial market analytics, technical indicators, and news sentiment. "
                "I cannot provide tax, legal, or accounting advice. Please consult a qualified tax professional "
                "or certified financial advisor for tax-related decisions."
            )

        return None

    def _get_grounded_market_context(self, tickers: list) -> str:
        """Fetch verified prices and sentiment to prevent hallucination of financial figures."""
        if not tickers:
            return ""

        from trading_engine import get_current_price
        from sentiment_service import get_sentiment

        context_lines = []
        for sym in tickers[:4]:
            sym_clean = sym.upper().strip()
            try:
                price = get_current_price(sym_clean)
                sent = get_sentiment(sym_clean)
                price_str = f"${price:.2f}" if price and price > 0 else "Live price unavailable"
                label = sent.get("label", "Neutral")
                score = sent.get("score", 0.0)
                n_articles = sent.get("sample_size", 0)

                context_lines.append(
                    f"- {sym_clean}: Current Price = {price_str} | Sentiment = {label} "
                    f"(Score: {score:+.2f}, N={n_articles} articles analyzed)"
                )
            except Exception:
                context_lines.append(f"- {sym_clean}: Market feed temporarily unavailable.")

        if context_lines:
            return "VERIFIED MARKET REALITY (DO NOT INVENT OR CONTRADICT THESE DATA POINTS):\n" + "\n".join(context_lines)
        return ""

    def _build_system_prompt(self, user_context, market_context=""):
        """Build system prompt with user context and verified market reality."""
        p_val = user_context.get('portfolio_value', 0)
        cash = user_context.get('cash_balance', 100000)
        pnl = user_context.get('total_pnl', 0)
        pnl_pct = user_context.get('total_pnl_pct', 0)
        win_rate = user_context.get('win_rate', 0)
        holdings = user_context.get('holdings', [])
        holdings_str = ', '.join(holdings) if holdings else 'None'
        
        return f"""You are a professional, polite, and helpful AI financial intelligence assistant for Sovereign Intelligence.
Your purpose is to assist users with portfolio analytics, market sentiment synthesis, and risk assessment.

CORE SAFETY & FACTUALITY RULES:
1. **NEVER FABRICATE PRICES, FINANCIAL METRICS, OR NEWS CITATIONS.** If price or fundamental data for a symbol is not provided in the verified context, explicitly state that live market data is unavailable.
2. **NO GUARANTEED RETURNS:** Never promise or imply guaranteed profits or risk-free trades. Remind users that investments involve risk of loss.
3. **NO AUTOMATIC EXECUTION:** Remind users that automated suggestions are informational and all trade orders must be reviewed and placed manually via the Trading Desk.
4. **PRIVACY PROTECTION:** Never expose user account credentials, database IDs, or private personal data in answers.
5. **OBJECTIVITY:** Maintain an objective, balanced tone. Do not make unsupported causal claims.

CURRENT ACCOUNT CONTEXT:
- Paper Equity: ${p_val:,.2f}
- Available Buying Power: ${cash:,.2f}
- Realized/Unrealized P&L: ${pnl:,.2f} ({pnl_pct:.2f}%)
- Monitored Holdings: {holdings_str}

{market_context}

CAPABILITIES:
- FinBERT & VADER sentiment interpretation
- Technical trend and portfolio risk assessment
- Strategy considerations (position sizing, stop-loss discipline)

Current UTC Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"""
    
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
