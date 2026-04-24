import os
import re
from io import BytesIO

from openai import OpenAI
from google import genai
from PIL import Image

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Нет TELEGRAM_TOKEN")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Нет DEEPSEEK_API_KEY")
if not WEBHOOK_URL:
    raise RuntimeError("Нет WEBHOOK_URL")

deepseek = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

openrouter = None
if OPENROUTER_API_KEY:
    openrouter = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

gemini = None
if GEMINI_API_KEY:
    gemini = genai.Client(api_key=GEMINI_API_KEY)

user_histories = {}

keyboard = [
    ["🤖 Спросить AI", "📸 Решить фото"],
    ["🧹 Очистить память", "📜 Помощь"],
    ["😎 Кто ты?"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clean_text(text: str) -> str:
    text = text or ""

    text = re.sub(
        r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}",
        r"\1/\2",
        text,
    )
    text = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"√\1", text)

    replacements = {
        "```": "",
        "$$": "",
        "$": "",
        "\\cdot": "×",
        "\\times": "×",
        "\\div": "÷",
        "\\left": "",
        "\\right": "",
        "\\approx": "≈",
        "\\quad": " ",
        "###": "",
        "**": "",
        "{": "",
        "}": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def send_long(update: Update, text: str):
    text = clean_text(text)

    if not text:
        text = "Ошибка обработки. Попробуй ещё раз."

    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i + 3900])


def ask_deepseek(messages) -> str:
    try:
        response = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )
        return response.choices[0].message.content

    except Exception as e:
        error = str(e)

        if openrouter:
            try:
                response = openrouter.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=1200,
                )
                return response.choices[0].message.content
            except Exception as e2:
                return "Ошибка fallback AI: " + str(e2)[:700]

        if "402" in error or "credit" in error.lower():
            return "⛔ Закончились кредиты DeepSeek."
        if "429" in error or "rate" in error.lower():
            return "⏳ Слишком много запросов. Попробуй позже."

        return "Ошибка AI: " + error[:700]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот.\n\n"
        "💬 Напиши вопрос\n"
        "📸 Или отправь фото с заданием",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Команды:\n"
        "/start — запуск\n"
        "/clear — очистить память\n"
        "/help — помощь\n\n"
        "📸 Для фото лучше снимай ближе и ровно."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Память очищена 🧹")
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        text = update.message.text or ""

        if text == "🧹 Очистить память":
            user_histories[user_id] = []
            await update.message.reply_text("Память очищена 🧹")
            return

        if text == "📜 Помощь":
            await help_command(update, context)
            return

        if text == "😎 Кто ты?":
            await update.message.reply_text(
                "Я AI-бот на Python + Telegram + DeepSeek + Render 🚀"
            )
            return

        if text == "📸 Решить фото":
            await update.message.reply_text("Отправь фото с заданием 📸")
            return

        if text == "🤖 Спросить AI":
            await update.message.reply_text("Напиши вопрос 🙂")
            return

        if user_id not in user_histories:
            user_histories[user_id] = []

        user_histories[user_id].append({"role": "user", "content": text})
        user_histories[user_id] = user_histories[user_id][-8:]

        messages = [
            {
                "role": "system",
                "content": (
                    "Ты дружелюбный AI-помощник. "
                    "Отвечай по-русски понятно и кратко. "
                    "Не спорь с пользователем. "
                    "Если не уверен — скажи, что не уверен. "
                    "Не используй LaTeX."
                ),
            }
        ] + user_histories[user_id]

        reply = ask_deepseek(messages)
        reply = clean_text(reply)

        user_histories[user_id].append({"role": "assistant", "content": reply})

        await send_long(update, reply)

    except Exception as e:
        print("Ошибка текста:", e)
        await update.message.reply_text("Ошибка: " + str(e)[:1000])


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not gemini:
            await update.message.reply_text(
                "Фото пока не включены: добавь GEMINI_API_KEY в Render Environment."
            )
            return

        await update.message.reply_text("Смотрю картинку 👀")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()

        image = Image.open(BytesIO(file_bytes)).convert("RGB")

        caption = update.message.caption or ""

        if "подробно" in caption.lower() or "решение" in caption.lower():
            prompt = (
                "Реши задания с картинки.\n"
                "Пиши обычным текстом для Telegram.\n"
                "Без LaTeX.\n"
                "Дроби пиши как 7/10.\n"
                "Корни пиши как √28.\n\n"
                "Формат:\n"
                "Задание 1:\n"
                "Решение:\n"
                "1) ...\n"
                "2) ...\n"
                "Ответ: ..."
            )
        else:
            prompt = (
                "Реши ВСЕ видимые примеры с картинки.\n"
                "Верни ТОЛЬКО финальные ответы.\n"
                "Без решения. Без объяснений. Без Markdown. Без LaTeX.\n\n"
                "ВАЖНО:\n"
                "7 над 10 = 7/10, НЕ 710.\n"
                "3 над 8 = 3/8, НЕ 38.\n"
                "1 над 5 = 1/5, НЕ 15.\n"
                "2 1/3 = смешанное число, НЕ 213.\n"
                "√28 = корень из 28.\n\n"
                "Формат строго:\n"
                "[4]\n"
                "[2]\n"
                "[3/8]\n"
                "[1/2]\n\n"
                "Если пример плохо видно — напиши [не видно]."
            )

        response = gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, image],
        )

        reply = clean_text(response.text)

        if not reply:
            reply = "Не смог разобрать фото 😅 Попробуй сфоткать ближе."

        await send_long(update, reply)

    except Exception as e:
        error = str(e)
        print("Ошибка фото:", error)

        if "429" in error or "quota" in error:
            lower()
            await update.message.reply_text("⏳ Лимит Gemini закончился. Попробуй позже.")
        else:
            await update.message.reply_text("Ошибка фото: " + error[:1000])


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("help", help_command))

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("AI бот запущен через webhook 🚀")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TELEGRAM_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
    drop_pending_updates=True,
)

	