import os

from groq import Groq
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

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

user_histories = {}

keyboard = [
    ["🤖 Спросить AI", "🧹 Очистить память"],
    ["📜 Помощь", "😎 Кто ты?"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот. Напиши любой вопрос.",
        reply_markup=markup,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — запуск\n"
        "/clear — очистить память\n"
        "/help — помощь"
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
                    "content": "Ты умный AI-помощник. Отвечай по-русски понятно и коротко."
                }
            ] + user_histories[user_id],
            temperature=0.7,
            max_completion_tokens=1000,
        )

        reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка:", e)
        await update.message.reply_text("Упс, ошибка 😅 Попробуй ещё раз.")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("AI бот запущен через webhook 🤖")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TELEGRAM_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
)