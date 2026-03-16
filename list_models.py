import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from google import genai
from dotenv import load_dotenv

load_dotenv()

def test():
    api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)
    
    print("--- Listing Models ---")
    try:
        for model in client.models.list():
            print(f"Model: {model.name}, Display: {model.display_name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    test()
