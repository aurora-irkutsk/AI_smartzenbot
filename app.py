import os
import replicate
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# === ГЛОБАЛЬНОЕ СОСТОЯНИЕ: кто ожидает ввод описания ===
user_states = {}

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "final-secret").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

# === ОБРАБОТЧИКИ ===

@router.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать картинку")],
            [KeyboardButton(text="🧹 Очистить контекст")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🧠 Привет! Я Smart-Zen.\n"
        "📝 Пиши любой вопрос — отвечу.\n"
        "🖼️ Нажми «Создать картинку», чтобы сгенерировать изображение по описанию!",
        reply_markup=kb
    )

@router.message(lambda msg: msg.text == "Создать картинку")
async def image_button(message: Message):
    user_states[message.from_user.id] = "awaiting_image_prompt"
    await message.answer(
        "🖼️ Отлично! Опишите, что вы хотите увидеть.\n\n"
        "Примеры:\n"
        "• футуристический город на закате\n"
        "• портрет девушки в стиле Ван Гога\n"
        "• a cute robot drinking coffee, cartoon style"
    )

@router.message(lambda msg: msg.text == "🧹 Очистить контекст")
async def clear_button(message: Message):
    user_states.pop(msg.from_user.id, None)
    await message.answer("🧠 Контекст очищен. О чём поговорим?")

@router.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    
    # Если пользователь ожидает ввод описания — генерируем картинку
    if user_states.get(user_id) == "awaiting_image_prompt":
        user_states.pop(user_id)  # Сбрасываем состояние
        
        if not message.text:
            await message.answer("🖼️ Пожалуйста, отправьте текстовое описание.")
            return
            
        prompt = message.text.strip()
        if not prompt:
            await message.answer("🖼️ Описание не должно быть пустым.")
            return

        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        try:
            output = replicate.run(
                "stability-ai/sdxl",
                input={"prompt": prompt}
            )
            if output and isinstance(output, list):
                await message.answer_photo(photo=output[0])
            else:
                await message.answer("❌ Не удалось создать изображение.")
        except Exception as e:
            print(f"🖼️ Replicate error: {e}")
            await message.answer("⚠️ Ошибка генерации. Попробуйте другое описание.")
    
    # Иначе — отвечаем через AI
    else:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY", "").strip()
            )
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — умный, знающий и вежливый помощник. "
                            "Никогда не упоминай, что ты ИИ, бот или программа. "
                            "Всегда отвечай на языке пользователя. "
                            "Будь кратким и по делу."
                        )
                    },
                    {"role": "user", "content": message.text}
                ],
                timeout=30.0
            )
            await message.answer(response.choices[0].message.content.strip())
        except Exception as e:
            await message.answer("⚠️ Временно не могу ответить.")

# === WEBHOOK И ЗАПУСК ===
dp.include_router(router)

async def on_startup(app):
    print(f"✅ Устанавливаю webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

def main():
    app = web.Application()
    SimpleRequestHandler(dp, bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    main()
