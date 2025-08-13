import os
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Dictionary to keep track of running FFmpeg processes
ffmpeg_processes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text("Welcome! Use /stream <m3u8_link> <rtmp_url> <stream_key> to start streaming.")

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stream command to start streaming M3U8 to RTMP."""
    user_id = update.effective_user.id
    args = context.args

    if len(args) != 3:
        await update.message.reply_text("Usage: /stream <m3u8_link> <rtmp_url> <stream_key>")
        return

    m3u8_link, rtmp_url, stream_key = args

    # Validate inputs (allow rtmp:// and rtmps://)
    if not m3u8_link.startswith(("http://", "https://")):
        await update.message.reply_text("Invalid M3U8 link (must start with http:// or https://).")
        return
    if not rtmp_url.startswith(("rtmp://", "rtmps://")):
        await update.message.reply_text("Invalid RTMP URL (must start with rtmp:// or rtmps://).")
        return

    # Stop any existing stream for this user
    if user_id in ffmpeg_processes:
        try:
            ffmpeg_processes[user_id].terminate()
            await update.message.reply_text("Previous stream stopped.")
        except Exception as e:
            logger.error(f"Error stopping previous stream for user {user_id}: {e}")
        finally:
            del ffmpeg_processes[user_id]

    # Construct FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", m3u8_link,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-f", "flv",
        f"{rtmp_url}{stream_key}"  # Combine RTMP URL and stream key without extra slash
    ]

    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        ffmpeg_processes[user_id] = process
        await update.message.reply_text("Streaming started successfully!")
        
        # Monitor FFmpeg process for errors
        _, stderr = process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg failed for user {user_id}: {stderr}")
            await update.message.reply_text(f"Stream failed: {stderr[:200]}... Check logs for details.")
            if user_id in ffmpeg_processes:
                del ffmpeg_processes[user_id]
    except Exception as e:
        logger.error(f"Error starting stream for user {user_id}: {e}")
        await update.message.reply_text(f"Failed to start stream: {str(e)}")
        if user_id in ffmpeg_processes:
            del ffmpeg_processes[user_id]

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stop command to stop the current stream."""
    user_id = update.effective_user.id
    if user_id in ffmpeg_processes:
        try:
            ffmpeg_processes[user_id].terminate()
            await update.message.reply_text("Stream stopped.")
        except Exception as e:
            logger.error(f"Error stopping stream for user {user_id}: {e}")
            await update.message.reply_text("Error stopping stream.")
        finally:
            del ffmpeg_processes[user_id]
    else:
        await update.message.reply_text("No active stream to stop.")

def main():
    """Main function to initialize and run the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not found in .env file")
        return

    # Initialize the bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stream", stream))
    application.add_handler(CommandHandler("stop", stop))

    # Start the bot
    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == "__main__":
    main()
