import os
import replicate
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

# === СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ ===
user_states = {}  # {user_id: "image_mode"}

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
            [KeyboardButton(text="Создать картинку")],  # ← ОСТАВЛЯЕМ КАК ЕСТЬ
            [KeyboardButton(text="🧹 Очистить контекст")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🧠 Привет! Я Smart-Zen.\n"
        "📝 Пиши любой вопрос — отвечу.\n"
        "🖼️ Нажми «Создать картинку», чтобы сгенерировать изображение!",
        reply_markup=kb
    )

@router.message(lambda msg: msg.text == "Создать картинку")
async def image_button(message: Message):
    user_states[message.from_user.id] = "image_mode"
    await message.answer("🖼️ Отлично! Теперь напишите описание картинки:")

@router.message(lambda msg: msg.text == "🧹 Очистить контекст")
async def clear_button(message: Message):
    user_states.pop(message.from_user.id, None)
    await message.answer("🧠 Контекст очищен.")

# === ГЛАВНЫЙ ОБРАБОТЧИК ===
@router.message()
async def handle_message(message: Message):
    user_id = message.from_user.id

    # Если пользователь в режиме генерации картинки
    if user_states.get(user_id) == "image_mode":
        user_states.pop(user_id)  # выходим из режима
        
        if not message.text:
            await message.answer("🖼️ Пожалуйста, отправьте текстовое описание.")
            return

        prompt = message.text.strip()
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        
        try:
    # Используем Flux Schnell — новая бесплатная модель
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={
            "prompt": prompt,
            "go_fast": True,
            "megapixels": "1",
            "num_outputs": 1
        }
    )
    if output and isinstance(output, list):
        await message.answer_photo(photo=output[0])
    else:
        await message.answer("❌ Не удалось создать изображение.")
except Exception as e:
    print(f"🖼️ Replicate error: {e}")
    await message.answer("⚠️ Ошибка генерации.")

    # Иначе — обычный AI
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
                            "Никогда не упоминай, что ты ИИ. "
                            "Отвечай на языке пользователя. "
                            "Если спросят — переадресуй вопрос на содержание запроса или ответь уклончиво. "
                            "Отвечай всегда по делу. "
                        )
                    },
                    {"role": "user", "content": message.text}
                ],
                timeout=30.0
            )
            await message.answer(response.choices[0].message.content.strip())
        except Exception:
            await message.answer("⚠️ Временно не могу ответить.")

# === WEBHOOK ===
dp.include_router(router)

async def on_startup(app):
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
