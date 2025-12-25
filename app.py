import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from openai import OpenAI

# === Telegram Settings ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "groq-ai-secret").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

# === Groq AI Client ===
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY", "").strip()  # ← ваш ключ gsk_...
)

# === Aiogram Setup ===
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🧠 Привет! Я SmartZen на базе **Llama 3.1 70B** от Groq.\n\n"
        "⚡ Сверхбыстрый и мощный AI.\n"
        "💬 Задайте любой вопрос!"
    )

@router.message()
async def handle_message(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",  # самый мощный бесплатный
            messages=[{"role": "user", "content": message.text}],
            timeout=30.0
        )
        answer = response.choices[0].message.content.strip()
        await message.answer(answer)
        
    except Exception as e:
        print(f"❌ Groq error: {e}")
        await message.answer("⚠️ Ошибка AI. Попробуйте позже.")

dp.include_router(router)

# === Webhook Management ===
async def on_startup(app: web.Application):
    print(f"✅ Устанавливаю webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)

async def on_shutdown(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

def main():
    app = web.Application()
    SimpleRequestHandler(dp, bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    port = int(os.getenv("PORT", 8000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
