import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "test").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start(message: Message):
    await message.answer("✅ Работает! Webhook активен.")

@router.message()
async def handle_message(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        # Инициализация Groq-клиента ВНУТРИ функции (безопасно)
        from openai import OpenAI
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",  # ← УБЕРИТЕ ПРОБЕЛЫ В КОНЦЕ!
            api_key=os.getenv("GROQ_API_KEY", "").strip()
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Актуальная модель
            messages=[{"role": "user", "content": message.text}],
            timeout=30.0
        )
        await message.answer(response.choices[0].message.content.strip())
        
    except Exception as e:
        print(f"❌ Groq error: {e}")
        await message.answer("⚠️ Ошибка AI. Попробуйте позже.")
        
    except Exception as e:
        print(f"❌ Groq error: {e}")
        await message.answer("⚠️ Ошибка AI. Попробуйте позже.")

dp.include_router(router)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    SimpleRequestHandler(dp, bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    main()
