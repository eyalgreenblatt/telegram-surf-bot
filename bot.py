import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

from surf_tools import get_surf_forecast
from surf_graph import create_wave_graph
from voice_tools import transcribe_voice
from voice_parser import parse_voice_command
from rating_system import format_good_windows_message

load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏄 Surf Bot Ready!\n\n"
        "Commands:\n"
        "  surf habonim 7 days  – 7-day forecast with graph\n"
        "  surf tel aviv        – today's forecast\n\n"
        "The bot will automatically alert you when the wave\n"
        "quality rating reaches 7/10 or above. 🌊"
    )


async def _send_forecast(update: Update, beach: str, days: int, lang: str) -> None:
    """Fetch forecast, send text report, graph, and good-wave notification."""
    report, hours, windows = get_surf_forecast(beach, days, lang)
    await update.message.reply_text(report)

    if hours:
        graph = create_wave_graph(hours, beach)
        with open(graph, "rb") as img:
            await update.message.reply_photo(img)

        # Automatic notification when good waves are detected (rating >= 7)
        notification = format_good_windows_message(windows, beach)
        if notification:
            await update.message.reply_text(
                notification,
                parse_mode="Markdown",
            )


async def surf_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    beach = "habonim" if "habonim" in text else "tel aviv"
    days = 7 if "7" in text else 1

    await _send_forecast(update, beach, days, "en")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    await file.download_to_drive("voice.ogg")

    transcribed_text = transcribe_voice("voice.ogg")
    beach, days, lang = parse_voice_command(transcribed_text, lang="he")

    duration_label = (
        "today" if days == 1
        else "tomorrow" if days == 2
        else f"{days} days"
    )
    await update.message.reply_text(
        f"🏄 Fetching forecast for {beach.title()}, {duration_label}..."
    )

    await _send_forecast(update, beach, days, lang)


def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, surf_chat))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling()


if __name__ == "__main__":
    main()
