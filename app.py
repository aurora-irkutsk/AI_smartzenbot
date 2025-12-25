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
    # Если это /start — уже обработано, поэтому сюда приходят ТОЛЬКО обычные сообщения
    user_text = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        api_key = os.getenv("QWEN_API_KEY", "").strip()
        if not api_key:
            await message.answer("❌ QWEN_API_KEY не задан в настройках.")
            return

        import dashscope
        dashscope.api_key = api_key
        # 🔥 УБРАЛ ПРОБЕЛЫ В КОНЦЕ!
        dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

        response = dashscope.Generation.call(
            model="qwen-max",
            messages=[{"role": "user", "content": user_text}],
            result_format="message"
        )

        if response.status_code == 200:
            ai_reply = response.output.choices[0].message.content.strip()
            await message.answer(ai_reply)
        else:
            error_msg = getattr(response, 'message', 'Неизвестная ошибка')
            await message.answer(f"❌ AI ошибка: {error_msg[:150]}")
            
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
