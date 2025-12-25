import os
import replicate
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
# Флаг для отслеживания, кто ожидает ввод описания картинки
awaiting_image_prompt = set()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "final-secret").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://aismartzenbot-smartzenbot.up.railway.app").strip()
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/image кот в очках")],
            [KeyboardButton(text="🧹 Очистить контекст")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🧠 Привет! Я Smart-Zen.\n"
        "📝 Пиши любой вопрос — отвечу.\n"
        "🖼️ Или нажми кнопку, чтобы создать изображение!",
        reply_markup=kb
    )

@router.message(lambda msg: msg.text == "🖼️ Создать картинку")
async def image_button(message: Message):
    await message.answer("🖼️ Напишите описание для картинки:\n\nПример: *кот в космосе, цифровое искусство*")

@router.message(lambda msg: msg.text == "🧹 Очистить контекст")
async def clear_button(message: Message):
    await message.answer("🧠 Контекст очищен. О чём поговорим?")

@router.message()
async def handle_message(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        from openai import OpenAI # type: ignore
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
                        "Ты — умный, знающий и вежливый помощник."
                        "Никогда не упоминай, что ты искусственный интеллект, бот, программа или модель."
                        "Не отвечай на вопросы о том, кто ты или как ты устроен."
                        "Всегда отвечай на том языке, на котором к тебе обратился пользователь."
                        "Если спросят — переадресуй вопрос на содержание запроса или ответь уклончиво."
                        "Отвечай всегда по делу."
                    )
                },
                {"role": "user", "content": message.text}
            ],
            timeout=30.0
        )
        await message.answer(response.choices[0].message.content.strip())
    except Exception as e:
        await message.answer("⚠️ Временно не могу ответить.")

dp.include_router(router)

@router.message(lambda msg: msg.text and "создать картинку" in msg.text.lower())
async def start_image_flow(message: Message):
    awaiting_image_prompt.add(message.from_user.id)
    await message.answer("🖼️ Отлично! Опишите, что вы хотите увидеть:")

@router.message(lambda msg: msg.from_user.id in awaiting_image_prompt and msg.text)
async def generate_image_from_text(message: Message):
    user_id = message.from_user.id
    prompt = message.text.strip()
    
    if not prompt:
        await message.answer("🖼️ Пожалуйста, напишите описание.")
        return

    # Убираем пользователя из режима ожидания
    awaiting_image_prompt.discard(user_id)
    
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    
    try:
        # Генерация через Stable Diffusion XL
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c7121092325b256878870e1030c52948382",
            input={
                "prompt": prompt,
                "num_inference_steps": 30,
                "guidance_scale": 7.5
            }
        )
        
        if output and isinstance(output, list):
            await message.answer_photo(photo=output[0])
        else:
            await message.answer("❌ Не удалось создать изображение.")
            
    except Exception as e:
        print(f"🖼️ Replicate error: {e}")
        await message.answer("⚠️ Ошибка генерации. Попробуйте другое описание.")

# 🔥 Обязательно: регистрация webhook
async def on_startup(app):
    print(f"✅ Устанавливаю webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    SimpleRequestHandler(dp, bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)      # ← ЭТО ОБЯЗАТЕЛЬНО
    app.on_shutdown.append(on_shutdown)    # ← ЭТО ОБЯЗАТЕЛЬНО
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

if __name__ == "__main__":
    main()
