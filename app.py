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
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-secret-path-here")  # для безопасности
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://fallback.up.railway.app")
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

@router.message()
async def handle_message(message: Message):
    user_text = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "qwen-max",
                "input": {
                    "messages": [{"role": "user", "content": user_text}]
                }
            }
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                error_text = response.text[:200]
                await message.answer(f"❌ Ошибка Qwen API ({response.status_code})")
                print(f"Qwen error: {error_text}")
                return

            data = response.json()
            ai_reply = data["output"]["choices"][0]["message"]["content"].strip()
            await message.answer(ai_reply)

    except Exception as e:
        print(f"Exception: {e}")
        await message.answer("⚠️ Произошла внутренняя ошибка. Попробуйте позже.")

dp.include_router(router)

# Обработка Webhook
async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)

async def on_shutdown(app: web.Application):
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
