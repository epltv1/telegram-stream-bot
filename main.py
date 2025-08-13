import os
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Dictionary to keep track of running FFmpeg processes
ffmpeg_processes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /stream <m3u8_link> <rtmp_url> <stream_key> to start streaming.")

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) != 3:
        await update.message.reply_text("Usage: /stream <m3u8_link> <rtmp_url> <stream_key>")
        return

    m3u8_link, rtmp_url, stream_key = args

    # Validate inputs (basic check)
    if not m3u8_link.startswith("http") or not rtmp_url.startswith("rtmp://"):
        await update.message.reply_text("Invalid M3U8 link or RTMP URL.")
        return

    # Stop any existing stream for this user
    if user_id in ffmpeg_processes:
        ffmpeg_processes[user_id].terminate()
        del ffmpeg_processes[user_id]
        await update.message.reply_text("Previous stream stopped.")

    # Construct FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", m3u8_link,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-f", "flv",
        f"{rtmp_url}/{stream_key}"
    ]

    try:
        # Start FFmpeg process
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_processes[user_id] = process
        await update.message.reply_text("Streaming started successfully!")
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        await update.message.reply_text(f"Failed to start stream: {str(e)}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ffmpeg_processes:
        ffmpeg_processes[user_id].terminate()
        del ffmpeg_processes[user_id]
        await update.message.reply_text("Stream stopped.")
    else:
        await update.message.reply_text("No active stream to stop.")

def main():
    # Initialize the bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stream", stream))
    application.add_handler(CommandHandler("stop", stop))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
