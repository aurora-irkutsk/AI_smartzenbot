import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# Инициализация DashScope
import dashscope
dashscope.api_key = os.getenv("QWEN_API_KEY", "").strip()
# 🔥 Убрали пробелы в URL!
dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

# Токены Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-this").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer("🧠 Привет! Я SmartZen — ваш AI-помощник. Задайте вопрос!")

@router.message()
async def handle_message(message: Message):
    user_text = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # 🔥 Правильное имя модели: qwen-max
        response = dashscope.Generation.call(
            model="qwen-max",
            messages=[{"role": "user", "content": user_text}],
            result_format="message"
        )
        if response.status_code == 200:
            ai_reply = response.output.choices[0].message.content.strip()
            await message.answer(ai_reply)
        else:
            await message.answer("❌ Ошибка AI: проверьте ключ и модель.")
    except Exception as e:
        print(f"Ошибка DashScope: {e}")
        await message.answer("⚠️ Внутренняя ошибка сервера.")

dp.include_router(router)

# Webhook функции
async def on_startup(app: web.Application):
    try:
        print(f"✅ Устанавливаю webhook: {WEBHOOK_URL}")
        await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    port = int(os.getenv("PORT", 8000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
