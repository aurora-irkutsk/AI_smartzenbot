import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

# Получаем токены из переменных окружения (Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

# Укажите вашу модель Qwen (пока qwen-max — можно изменить позже)
QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# Инициализация
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer(
        "🧠 Привет! Я SmartZen — ваш AI-помощник на базе Qwen.\n\n"
        "💡 Задайте любой вопрос: о технологиях, жизни, учёбе, бизнесе — и я постараюсь помочь!"
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
                    "messages": [
                        {"role": "user", "content": user_text}
                    ]
                }
            }
            response = await client.post(QWEN_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            ai_reply = data["output"]["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"Ошибка: {e}")
        ai_reply = "⚠️ Извините, произошла ошибка. Проверьте API-ключ или попробуйте позже."

    await message.answer(ai_reply)

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())