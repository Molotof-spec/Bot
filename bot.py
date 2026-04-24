import os
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

client = Groq(api_key=GROQ_API_KEY)

TEXT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

user_histories = {}

keyboard = [
    ["🤖 Спросить AI", "🧹 Очистить память"],
    ["📜 Помощь", "😎 Кто ты?"],
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clean_text(text):
    text = text or ""

    replacements = {
        "\\sqrt": "sqrt",
        "\\frac": "",
        "\\cdot": "×",
        "\\times": "×",
        "\\div": "÷",
        "\\left": "",
        "\\right": "",
        "\\approx": "≈",
        "\\": "",
        "$": "",
        "```": "",
        "###": "",
        "**": "",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = text.replace("{", "").replace("}", "")

    return text.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот. Отправь фото с заданием или напиши вопрос.",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Что я умею:\n"
        "• отвечать на вопросы\n"
        "• решать задания с фото\n"
        "• очищать память кнопкой 🧹\n\n"
        "Команды:\n"
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
        image_url = file.file_path

        prompt = update.message.caption or (
            "Реши ВСЕ примеры с картинки.\n"
            "Верни ТОЛЬКО финальные ответы.\n"
            "Без решения, без объяснений, без Markdown, без LaTeX.\n"
            "Каждый ответ пиши с новой строки строго в квадратных скобках.\n"
            "Пример:\n"
            "[4]\n"
            "[113/63]\n"
            "[1,25]\n"
            "Если пример плохо видно, пропусти его."
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
            max_completion_tokens=1200,
        )

        reply = clean_text(response.choices[0].message.content)

        if not reply:
            reply = "Не смог разобрать картинку 😅 Попробуй сфоткать ближе и чётче."

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка фото:", e)
        await update.message.reply_text("Ошибка фото: " + str(e)[:1000])


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
            await update
            message.reply_text("Я AI-бот на Python + Telegram + Groq + Render 🚀")
            return

        if text == "🤖 Спросить AI":
            await update.message.reply_text("Напиши свой вопрос 🙂")
            return

        if user_id not in user_histories:
            user_histories[user_id] = []

        user_histories[user_id].append({"role": "user", "content": text})
        user_histories[user_id] = user_histories[user_id][-10:]

        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты умный AI-помощник. Отвечай по-русски понятно и кратко. "
                        "Не используй LaTeX. Для математики используй обычные символы: × ÷ /."
                    ),
                }
            ] + user_histories[user_id],
            temperature=0.7,
            max_completion_tokens=1000,
        )

        reply = clean_text(response.choices[0].message.content)

        if not reply:
            reply = "Ошибка обработки. Попробуй ещё раз."

        user_histories[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка текста:", e)
        await update.message.reply_text("Ошибка: " + str(e)[:1000])


if not TELEGRAM_TOKEN:
    raise RuntimeError("Нет TELEGRAM_TOKEN в Environment")
if not GROQ_API_KEY:
    raise RuntimeError("Нет GROQ_API_KEY в Environment")
if not WEBHOOK_URL:
    raise RuntimeError("Нет WEBHOOK_URL в Environment")


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
prompt = (
    "На картинке примеры по математике. "
    "Реши их и верни ТОЛЬКО финальные ответы.\n\n"
    "Формат строго:\n"
    "а) ответ\n"
    "б) ответ\n"
    "в) ответ\n"
    "г) ответ\n\n"
    "НЕ пиши решение. "
    "НЕ пиши шаги. "
    "НЕ используй LaTeX. "
    "Корень пиши как √, например √28. "
    "Если пример не видно — напиши: не видно."
)