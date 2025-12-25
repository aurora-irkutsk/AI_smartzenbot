import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "test-secret").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start(message: Message):
    await message.answer("✅ Бот работает! Webhook активен.")

# 🔥 ОДИН обработчик для всех сообщений
@router.message()
async def handle_message(message: Message):
    print(f"📩 Получено: '{message.text}'")
    await message.answer("🎯 Тест: сервер получил ваше сообщение!")
    
    try:
        api_key = os.getenv("QWEN_API_KEY", "").strip()
        print(f"🔑 Длина ключа: {len(api_key)}")  # Должно быть > 30
        
        if not api_key:
            await message.answer("❌ Ключ не задан.")
            return

        import dashscope
        dashscope.api_key = api_key
        dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

        response = dashscope.Generation.call(
            model="qwen-turbo",  # ← временно qwen-turbo
            messages=[{"role": "user", "content": message.text}],
            result_format="message"
        )

        print(f"📊 Статус: {response.status_code}")
        if response.status_code == 200:
            await message.answer(response.output.choices[0].message.content.strip())
        else:
            msg = getattr(response, 'message', 'Ошибка')
            await message.answer(f"❌ {msg}")
            
    except Exception as e:
        print(f"💥 ОШИБКА: {e}")
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")
            
    except Exception as e:
        print(f"💥 Qwen exception: {e}")
        await message.answer("⚠️ Ошибка сервера. Попробуйте позже.")

dp.include_router(router)

async def on_startup(app):
    print(f"✅ Setting webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    SimpleRequestHandler(dp, bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    port = int(os.getenv("PORT", 8000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
