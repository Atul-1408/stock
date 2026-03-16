import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

# Load Token from .env
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    TOKEN = input("Enter your Bot Token from BotFather: ")

async def get_chat_id():
    bot = Bot(token=TOKEN)
    print(f"Listening for messages on Bot (Token: {TOKEN[:5]}...)...")
    print("Please send a message like 'Hello' to your bot on Telegram NOW.")
    
    offset = 0
    while True:
        try:
            updates = await bot.get_updates(offset=offset)
            for update in updates:
                if update.message:
                    print(f"\n[OK] SUCCESS! Found Message.")
                    print(f"From: {update.message.from_user.first_name}")
                    print(f"👇 YOUR CHAT ID IS:")
                    print(f"{update.message.chat_id}")
                    return
                offset = update.update_id + 1
        except Exception as e:
            print(f"Error: {e}")
        
        await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(get_chat_id())
    except KeyboardInterrupt:
        pass

