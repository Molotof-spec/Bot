import os
import base64

from groq import Groq
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

client = Groq(api_key=GROQ_API_KEY)

TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

user_histories = {}

keyboard = [
    ["🤖 Спросить AI", "🧹 Очистить память"],
    ["📜 Помощь", "😎 Кто ты?"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


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
        "Отправь фото с задачей — я попробую решить красиво."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Память очищена 🧹")

def clean_reply(text):
    text = text.replace("$$", "")
    text = text.replace("###", "")
    text = text.replace("**", "")
    text = text.replace("\\cdot", "×")
    text = text.replace("\\div", "÷")
    text = text.replace("\\times", "×")
    text = text.replace("\\frac", "")
    text = text.replace("\\", "")
    text = text.replace("$", "")
    return text.strip()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Смотрю картинку 👀")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_url = file.file_path

        caption = update.message.caption or (
    		"Реши задания с картинки. "
    		"Пиши обычным текстом для Telegram. "
    		"СТРОГО ЗАПРЕЩЕНО использовать LaTeX, символы $, $$, \\frac, \\cdot, \\div, ###, Markdown. "
    		"Формат:\n"
    		"Пример 1:\n"
    		"Решение:\n"
    		"1) ...\n"
    		"2) ...\n"
    		"Ответ: ..."
	)


        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": caption},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            temperature=0.2,
            max_completion_tokens=1200,
        )

        reply = clean_reply(response.choices[0].message.content)
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
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты умный AI-помощник.Отвечай по-русски понятно и красиво. "
                        "Не используй LaTeX, если пользователь не просит. "
                        "Для математики используй обычные символы: × ÷ /."
                    )
                }
            ] + user_histories[user_id],
            temperature=0.7,
            max_completion_tokens=1000,
        )

        reply = clean_reply(response.choices[0].message.content)
        user_histories[user_id].append({"role": "assistant", "content": reply})

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