import os
import re
import base64
from together import Together

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Нет TELEGRAM_TOKEN")
if not TOGETHER_API_KEY:
    raise RuntimeError("Нет TOGETHER_API_KEY")
if not WEBHOOK_URL:
    raise RuntimeError("Нет WEBHOOK_URL")

client = Together(api_key=TOGETHER_API_KEY)

TEXT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
VISION_MODEL = "meta-llama/Llama-Vision-Free"

user_histories = {}

keyboard = [
    ["🤖 Спросить AI", "🧹 Очистить память"],
    ["📜 Помощь", "😎 Кто ты?"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clean_text(text: str) -> str:
    text = text or ""

    text = re.sub(r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", text)
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


def ask_text(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты дружелюбный AI-помощник. "
                        "Отвечай по-русски кратко и понятно. "
                        "Не спорь с пользователем. "
                        "Если не уверен — скажи, что не уверен. "
                        "Не используй LaTeX."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1000,
        )

        return response.choices[0].message.content

    except Exception as e:
        error = str(e)
        if "429" in error or "quota" in error.lower() or "rate" in error.lower():
            return "⏳ Лимит запросов. Попробуй позже."
        return "Ошибка 🤖: " + error[:500]


def ask_photo(prompt: str, image_base64: str) -> str:
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=1200,
        )

        return response.choices[0].message.content

    except Exception as e:
        error = str(e)
        if "429" in error or "quota" in error.lower() or "rate" in error.lower():
            return "⏳ Лимит запросов. Попробуй позже."
        return "Ошибка фото 🤖: " + error[:500]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 😎 Я AI-бот.\n\n"
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
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")

        caption = update.message.caption or ""

        if "решение" in caption.lower() or "подробно" in caption.lower():
            prompt = (
                "Реши задания с картинки.\n"
                "Пиши обычным текстом для Telegram.\n"
                "НЕ используй LaTeX.\n"
                "Дроби пиши так: 7/10, 3/8, 1/5.\n"
                "Корень пиши так: √28.\n\n"
                "Формат:\n"
                "Задание 1:\n"
                "Решение:\n"
                "1) ...\n"
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
                "2 1/3 = смешанное число, НЕ 213.\n\n"
                "Формат строго:\n"
                "[4]\n"
                "[2]\n"
                "[3/8]\n"
                "[1/2]\n\n"
                "Если пример плохо видно — напиши [не видно]."
            )

        reply = ask_photo(prompt, image_base64)
        await send_long(update, reply)

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
            await update.message.reply_text("Я AI-бот на Python + Telegram + Together AI + Render 🚀")
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
            "Отвечай по-русски понятно и кратко.\n"
            "Не используй LaTeX.\n\n"
            f"История:\n{history}\n\n"
            "Ответ:"
        )

        reply = ask_text(prompt)

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
app.add_handler(MessageHandler(filters.TEXT & ~filters)
(COMMAND, handle_text))

print("AI бот запущен через Together webhook 🤖")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TELEGRAM_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
    drop_pending_updates=True,
)