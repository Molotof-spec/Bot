import os

from groq import Groq
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

client = Groq(api_key=GROQ_API_KEY)

TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

keyboard = [
    ["🤖 Спросить AI", "🧹 Очистить память"],
    ["📜 Помощь", "😎 Кто ты?"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
user_histories = {}


def clean_text(text: str) -> str:
    text = text.replace("$$", "")
    text = text.replace("$", "")
    text = text.replace("\\frac", "")
    text = text.replace("\\cdot", "×")
    text = text.replace("\\div", "÷")
    text = text.replace("\\left", "")
    text = text.replace("\\right", "")
    text = text.replace("\\approx", "≈")
    text = text.replace("###", "")
    text = text.replace("**", "")
    text = text.replace("{", "")
    text = text.replace("}", "")
    return text.strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот. Напиши вопрос или отправь фото.",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — запуск\n"
        "/clear — очистить память\n"
        "/help — помощь\n\n"
        "Отправь фото с заданием — я решу его."
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
        image_url = file.file_path

        prompt = update.message.caption or (
           "На картинке школьные примеры. Сначала внимательно распознай дроби и смешанные числа. "
           "ВАЖНО: если видишь 7 над 10 — это 7/10, а не 710. "
           "Если видишь 2 1/3 — это смешанное число 2 + 1/3.\n\n"
           "Реши ВСЕ примеры. Верни ТОЛЬКО финальные ответы, без решения. "
           "Каждый ответ с новой строки строго в квадратных скобках.\n"
           "Пример:\n"
           "[4]\n"
           "[113/63]\n"
           "[1,25]\n"
           "Не используй LaTeX и объяснения."
       )

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            temperature=0.1,
            max_completion_tokens=1000,
        )

        reply = clean_text(response.choices[0].message.content)

        if not reply:
            reply = "Не смог разобрать картинку 😅 Попробуй фото чётче."

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка фото:", e)
        await update.message.reply_text("Ошибка фото: " + str(e)[:1000])


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "🧹 Очистить память":
        user_histories[user_id] = []
        await update.message.reply_text("Память очищена 🧹")
        return

    if text == "📜 Помощь":
        await help_command(update, context)
        return

    if text == "😎 Кто ты?":
        await update.message.reply_text("Я AI-бот на Python + Telegram + Groq + Render 🚀")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})
    user_histories[user_id] = user_histories[user_id][-10:]

    try:
        response = client.chat.completions(
            model=TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты умный AI-помощник. Отвечай по-русски понятно и кратко. "
                        "Не используй LaTeX."
                    ),
                }
            ]
            + user_histories[user_id],
            temperature=0.7,
            max_completion_tokens=1000,
        )

        reply = clean_text(response.choices[0].message.content)
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if not reply:
            reply = "Ошибка обработки. Попробуй ещё раз."

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка текста:", e)
        await update.message.reply_text("Ошибка: " + str(e)[:1000])


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
