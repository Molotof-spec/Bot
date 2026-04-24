from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from groq import Groq
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

user_histories = {}

keyboard = [
    ["🧠 Спросить AI", "🧹 Очистить память"],
    ["📚 Помощь", "😎 Кто ты?"]
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я твой AI-бот.\n\nПиши любой вопрос — я отвечу.",
        reply_markup=markup
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Память очищена 🧹")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/start — запустить бота\n"
        "/clear — очистить память\n"
        "/help — помощь\n\n"
        "Просто напиши сообщение, и я отвечу как AI 🤖"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("Я AI-бот на Python + Telegram + Groq 🤖")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})

    user_histories[user_id] = user_histories[user_id][-10:]

    try:
        response = client.chat.completions.create(
    	model="llama-3.3-70b-versatile",
        messages=[
	{
    		"role": "system",
    		"content": "Ты умный AI-помощник. Отвечай точно, понятно, проверяй логику, объясняй простыми словами. Если не 			                уверен — честно скажи."
	}
            ] + user_histories[user_id]
        )

        reply = response.choices[0].message.content

        user_histories[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply)

    except Exception as e:
        print("Ошибка:", e)
        await update.message.reply_text("Упс, что-то пошло не так 😅 Попробуй ещё раз.")


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("help", help_command))

from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_bot():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("AI бот запущен 🤖")
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)