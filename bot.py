import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters, CommandHandler
from groq import Groq

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

VISION_MODEL = "llava-v1.5-7b-4096"

# === ОЧИСТКА ТЕКСТА ===
def clean_text(text: str) -> str:
    lines = text.split("\n")
    result = []

    for line in lines:
        line = line.strip()

        if line and any(char.isdigit() for char in line):
            result.append(line)

    if not result:
        return text

    return "\n".join(result)


# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправь фото задания 📸")


# === ОБРАБОТКА ФОТО ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Смотрю картинку 👀")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_url = file.file_path

        caption = update.message.caption or (
            "Реши ВСЕ примеры с картинки.\n\n"
            "ВАЖНО:\n"
            "- Пиши ТОЛЬКО ответы\n"
            "- БЕЗ решения\n"
            "- БЕЗ объяснений\n"
            "- Каждая строка = один ответ\n"
            "- Формат строго: [ответ]\n\n"
            "Пример:\n"
            "[4]\n"
            "[113/63]\n"
            "[1,25]"
        )

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": caption},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )

        reply = clean_text(response.choices[0].message.content)

        if not reply.strip():
            reply = "Ошибка обработки. Попробуй ещё раз."

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("Ошибка:", e)
        await update.message.reply_text("Ошибка: " + str(e))


# === ТЕКСТ ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправь фото с заданием 📸")


# === ЗАПУСК ===
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT, handle_text))

app.run_polling()