import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from src.chatbot_engine import TradingChatbot

def test_chatbot():
    print("Testing Chatbot Initialization...")
    try:
        bot = TradingChatbot()
        if bot.client:
            print("✅ Success: Gemini Client initialized.")
        else:
            print("❌ Failure: Gemini Client is None.")
            
        # Try a dummy call if initialized
        if bot.client:
            print("Attempting to get a response (this requires a valid key)...")
            # Note: This might still fail if the key is invalid, but we're testing initialization first.
            response = bot.get_response(1, "Hello, are you working?")
            print(f"Response: {response['response'][:100]}...")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_chatbot()
