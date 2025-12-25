import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# Убираем глобальную инициализацию dashscope!
import dashscope  # импортируем, но не настраиваем сразу

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
    await message.answer("🧠 Привет! Я SmartZen. Задайте вопрос!")

@router.message()
async def handle_message(message: Message):
    user_text = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # 🔥 Инициализируем API ключ внутри функции
        api_key = os.getenv("QWEN_API_KEY", "").strip()
        if not api_key:
            await message.answer("❌ Ошибка: QWEN_API_KEY не задан в настройках.")
            return
        
        # Устанавливаем ключ и URL перед вызовом
        dashscope.api_key = api_key
        dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
        
        response = dashscope.Generation.call(
            model="qwen-max",
            messages=[{"role": "user", "content": user_text}],
            result_format="message"
        )
        print(f"📊 Qwen ответ: status={response.status_code}, request_id={response.request_id}")
        if response.status_code == 200:
            ai_reply = response.output.choices[0].message.content.strip()
            await message.answer(ai_reply)
        else:
            error_msg = getattr(response, 'message', str(response))
            print(f"❌ Ошибка Qwen: {error_msg}")
            await message.answer(f"❌ AI ошибка {response.status_code}: {error_msg[:150]}")
            
    except Exception as e:
        print(f"💥 Исключение: {e}")
        await message.answer("⚠️ Серверная ошибка. Проверьте логи.")

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
