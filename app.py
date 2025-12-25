import os
import asyncio
import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Токены
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-this").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

# Инициализация
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "🧠 Привет! Я SmartZen — ваш AI-помощник на базе Qwen.\n\n"
        "💡 Задайте любой вопрос!"
    )

from openai import OpenAI, OpenAIError
import os

# Инициализация клиента (лучше вынести за пределы функции)
qwen_client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY", "").strip(),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

@router.message()
async def handle_message(message: Message):
    user_text = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Запрос к Qwen через OpenAI-совместимый API
        completion = qwen_client.chat.completions.create(
            model="qwen-max",  # ✅ Правильное имя модели
            messages=[
                {"role": "user", "content": user_text}
            ],
            timeout=30.0
        )
        ai_reply = completion.choices[0].message.content.strip()
        await message.answer(ai_reply)

    except OpenAIError as e:
        print(f"❌ Qwen API error: {e}")
        await message.answer("⚠️ Ошибка AI. Проверьте ключ и квоту.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        await message.answer("⚠️ Внутренняя ошибка сервера.")

# Обработка Webhook
async def on_startup(app: web.Application):
    try:
        print(f"🔧 Setting webhook to: '{WEBHOOK_URL}'")
        await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)
        print("✅ Webhook set successfully!")
    except Exception as e:
        print(f"❌ FAILED to set webhook: {e}")

async def on_shutdown(app: web.Application):
    print("🧹 Cleaning up webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

def main():
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    main()
