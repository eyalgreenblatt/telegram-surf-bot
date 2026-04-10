import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

from surf_tools import get_surf_forecast
from surf_graph import create_wave_graph
from voice_tools import transcribe_voice

load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "?? Surf Bot Ready!\n\n"
        "Example:\n"
        "surf habonim 7 days\n"
        "?? ??? ????? ????? ??"
    )

async def surf_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    beach = "habonim" if "habonim" in text else "tel aviv"
    days = 7 if "7" in text else 1

    report, hours = get_surf_forecast(beach, days, "en")
    await update.message.reply_text(report)

    if hours:
        graph = create_wave_graph(hours, beach)
        with open(graph, "rb") as img:
            await update.message.reply_photo(img)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")

    text = transcribe_voice("voice.ogg")
    report, hours = get_surf_forecast("habonim", 7, "he")
    await update.message.reply_text(report)

def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, surf_chat))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling()

if __name__ == "__main__":
    main()
