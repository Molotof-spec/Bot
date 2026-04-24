import os
import re
from io import BytesIO

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Нет TELEGRAM_TOKEN")
if not GEMINI_API_KEY:
    raise RuntimeError("Нет GEMINI_API_KEY")
if not WEBHOOK_URL:
    raise RuntimeError("Нет WEBHOOK_URL")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate(prompt):
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            return model.generate_content(prompt).text
        except Exception as e:
            if "429" in str(e):
                continue
            else:
                return "Ошибка 🤖"
    return "⌛ Все лимиты исчерпаны"
user_histories = {}

keyboard = [
    ["🤖 Спросить AI", "🧹 Очистить память"],
    ["📜 Помощь", "😎 Кто ты?"],
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clean_text(text: str) -> str:
    import re

    text = text or ""

    # сначала правильно превращаем LaTeX-дроби в обычные дроби
    text = re.sub(r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", text)

    # корни
    text = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"√\1", text)
    text = re.sub(r"\\sqrt\s*([0-9]+)", r"√\1", text)

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
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

async def send_long(update: Update, text: str):
    text = clean_text(text)

    if not text:
        text = "Ошибка обработки. Попробуй ещё раз."

    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i + 3900])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот на Gemini.\n\n"
        "📸 Отправь фото с заданием.\n"
        "💬 Или напиши вопрос.",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Что я умею:\n"
        "• отвечать на вопросы\n"
        "• решать задания с фото\n"
        "• очищать память кнопкой 🧹\n\n"
        "/start — запуск\n"
        "/clear — очистить память\n"
        "/help — помощь"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Память очищена 🧹")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Смотрю картинку 👀")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()

        image = Image.open(BytesIO(file_bytes)).convert("RGB")

        prompt = (
            "Реши ВСЕ видимые примеры с картинки.\n"
            "Верни ТОЛЬКО финальные ответы.\n"
            "Без решения. Без объяснений. Без Markdown. Без LaTeX.\n"
            "Дроби пиши так: 7/10. Корень пиши так: √28.\n"
            "Если пример плохо видно — напиши [не видно]."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, image],
        )

        reply = clean_text(response.text)
        await send_long(update, reply)

    except Exception as e:
        print("Ошибка фото:", e)
        await update.message.reply_text("Ошибка фото: " + str(e)[:1000])
def generate(prompt):
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                continue
            else:
                return "Ошибка 🤖"

    return "⏳ Все лимиты исчерпаны"


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
            await update.message.reply_text("Я AI-бот на Python + Telegram + Gemini + Render 🚀")
            return

        if text == "🤖 Спросить AI":
            await update.message.reply_text("Напиши вопрос 🙂")
            return

        if user_id not in user_histories:
            user_histories[user_id] = []

        user_histories[user_id].append(f"Пользователь: {text}")
        user_histories[user_id] = user_histories[user_id][-8:]

        history = "\n".join(user_histories[user_id])

        prompt = (
            "Ты умный AI-помощник. Отвечай по-русски понятно и кратко.\n"
            "Не используй LaTeX. Для математики используй обычный текст.\n\n"
            f"История:\n{history}\n\n"
            "Ответ:"
        )

        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
        )

        reply = clean_text(response.text)

        if not reply:
            reply = "Ошибка обработки. Попробуй ещё раз."

        user_histories[user_id].append(f"Бот: {reply}")
        await send_long(update, reply)

    except Exception as e:
        print("Ошибка текста:", e)
        await update.message.reply_text("Ошибка: " + str(e)[:1000])


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("AI бот запущен через Gemini webhook 🤖")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TELEGRAM_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
    drop_pending_updates=True,
)