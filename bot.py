from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from groq import Groq
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

user_histories = {}

keyboard = [
[24.04.2026 17:05] Иван: import os
import base64
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY не задан")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL не задан")

client = Groq(api_key=GROQ_API_KEY)

TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

user_histories = {}

keyboard = [
    ["🧠 Спросить AI", "🖼 Анализ фото"],
    ["🧹 Очистить память", "📚 Помощь"],
    ["😎 Кто ты?", "🎲 Факт"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот.\n\n"
        "Я умею:\n"
        "• отвечать на вопросы\n"
        "• помнить контекст\n"
        "• понимать картинки\n"
        "• делать краткий разбор фото\n\n"
        "Напиши текст или отправь картинку.",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Команды:\n\n"
        "/start — запуск\n"
        "/clear — очистить память\n"
        "/help — помощь\n\n"
        "🖼 Чтобы я понял картинку — просто отправь фото.\n"
        "Можно добавить подпись, например: «что тут не так?»"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Память очищена 🧹")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "🧹 Очистить память":
        user_histories[user_id] = []
        await update.message.reply_text("Память очищена 🧹")
        return

    if text == "📚 Помощь":
        await help_command(update, context)
        return

    if text == "😎 Кто ты?":
        await update.message.reply_text(
            "Я твой AI-бот на Python + Telegram + Groq 🚀\n"
            "Работаю на Render через webhook."
        )
        return

    if text == "🖼 Анализ фото":
        await update.message.reply_text("Отправь мне фото, и я его разберу 🖼")
        return

    if text == "🎲 Факт":
        text = "Расскажи один короткий интересный факт."

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})
    user_histories[user_id] = user_histories[user_id][-10:]

    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты умный дружелюбный AI-помощник. "
                        "Отвечай по-русски, понятно, без воды. "
                        "Если пользователь просит код — давай готовый рабочий код. "
                        "Если не уверен — честно скажи."
                    ),
                }
            ]
            + user_histories[user_id],
            temperature=0.7,
            max_completion_tokens=1200,
        )

        reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка текста:", e)
        await update.message.reply_text("Упс, ошибка при ответе 😅 Попробуй ещё раз.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Смотрю картинку 👀")

        photo = update.message.
        file = await photo.get_file()
        photo_bytes = await file.download_as_bytearray()

        image_base64 = base64.b64encode(photo_bytes).decode("utf-8")

        caption = update.message.caption or (
            "Опиши картинку. Если на ней есть текст, прочитай его. "
            "Если есть проблема или ошибка, объясни что делать."
        )

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты помощник, который анализирует изображения. "
                        "Отвечай по-русски. Будь точным и полезным."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": caption},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                },
            ],
            temperature=0.3,
            max_completion_tokens=1200,
        )

        reply = response.choices[0].message.content
        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка фото:", e)
        await update.message.reply_text(
            "Не смог разобрать картинку 😅 Возможно, фото слишком большое или Groq временно не отвечает."
        )


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("AI бот запущен через webhook 🤖")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TELEGRAM_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
)	