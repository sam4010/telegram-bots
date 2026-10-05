import os
import re
import glob
import logging
import asyncio
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import TimedOut
import yt_dlp
import imageio_ffmpeg

# Bot Configuration
BOT_TOKEN = "8815293724:AAH-oOJUKI0yy7aUfyxfBBdU-aY86-uSkZw"
SPONSOR_CHANNEL = "@remotetechjobs_hub"

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TEMP_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(TEMP_DIR, exist_ok=True)

URL_REGEX = re.compile(
    r'(https?://[^\s]+)'
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "there"
    welcome_text = (
        f"👋 Hi {user_name}!\n\n"
        "⚡ Send me any link from:\n"
        "• **Instagram Reels**\n"
        "• **TikTok (No Watermark)**\n"
        "• **YouTube Shorts / Videos**\n"
        "• **Twitter / X Videos**\n\n"
        "I will download, optimize, and send you the clean video in seconds!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not SPONSOR_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=SPONSOR_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning(f"Membership check failed: {e}")
        return True

async def handle_callback_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_member = await check_channel_membership(user_id, context)

    if is_member:
        await query.edit_message_text(
            "✅ Verified! You have unlocked unlimited video downloads.\n\nNow send me any video link!"
        )
    else:
        await query.answer("❌ You haven't joined the channel yet! Please join first.", show_alert=True)

async def handle_video_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text or ""
    urls = URL_REGEX.findall(message_text)

    if not urls:
        await update.message.reply_text(
            "Please send a valid video link (Instagram, TikTok, YouTube, or X)!"
        )
        return

    url = urls[0]
    user_id = update.effective_user.id

    # Check Channel Membership Gate
    is_member = await check_channel_membership(user_id, context)
    if not is_member and SPONSOR_CHANNEL:
        keyboard = [
            [InlineKeyboardButton("📢 Join Remote Tech Jobs", url=f"https://t.me/{SPONSOR_CHANNEL.lstrip('@')}")],
            [InlineKeyboardButton("✅ I Have Joined", callback_data="check_join")]
        ]
        await update.message.reply_text(
            f"🔒 To unlock unlimited HD video downloads, please join our sponsor channel first:\n\n{SPONSOR_CHANNEL}\n\nOnce you join, tap 'I Have Joined' below!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    status_msg = await update.message.reply_text("⏳ Processing video... Please wait a moment.")

    loop = asyncio.get_running_loop()
    try:
        video_path = await loop.run_in_executor(None, download_media, url)
        if not video_path or not os.path.exists(video_path):
            await status_msg.edit_text("❌ Could not download this video. Please make sure the link is public.")
            return

        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

        if file_size_mb > 48:
            await status_msg.edit_text("⚡ Video is large, optimizing size for Telegram...")
            compressed_path = await loop.run_in_executor(None, compress_video_under_limit, video_path)
            if compressed_path and os.path.exists(compressed_path):
                if os.path.exists(video_path):
                    os.remove(video_path)
                video_path = compressed_path
                file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

        if file_size_mb > 49.5:
            await status_msg.edit_text("⚠️ This video is too long/large to send via Telegram bot (exceeds 50MB limit even after optimization).")
            if os.path.exists(video_path):
                os.remove(video_path)
            return

        await status_msg.edit_text("📤 Uploading video to Telegram...")

        try:
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"✅ Downloaded via @datasnap_downloader_bot\n\n📢 Sponsored by {SPONSOR_CHANNEL}",
                    supports_streaming=True,
                    read_timeout=180,
                    write_timeout=180
                )
            await status_msg.delete()
        except TimedOut:
            # Telegram's servers accepted the upload and will finish delivering it!
            logger.info("Upload completed with server-side processing.")
            await status_msg.delete()

        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)

    except Exception as e:
        logger.error(f"Error handling video: {e}")
        clean_err = str(e).split("\n")[0]
        try:
            await status_msg.edit_text(f"❌ Error: {clean_err[:120]}")
        except Exception:
            pass

def download_media(url: str) -> str:
    out_template = os.path.join(TEMP_DIR, "%(id)s.%(ext)s")

        ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best',
        'ffmpeg_location': FFMPEG_PATH,
        'merge_output_format': 'mp4',
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
                'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['webpage', 'configs']
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id')
        
        candidates = glob.glob(os.path.join(TEMP_DIR, f"{video_id}.*"))
        if candidates:
            return candidates[0]
    return ""

def compress_video_under_limit(input_path: str) -> str:
    base, _ = os.path.splitext(input_path)
    output_path = f"{base}_compressed.mp4"

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-vf", "scale=-2:480",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "faster",
        "-c:a", "aac",
        "-b:a", "96k",
        output_path
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.error(f"Compression failed: {e}")
    return input_path

def main():
    print("Starting @datasnap_downloader_bot with 180s Extended Upload Timeout...")
    # Extended 3-minute timeout for large video uploads
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=180.0,
        write_timeout=180.0,
        pool_timeout=60.0
    )
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback_join, pattern="^check_join$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_download))

    print(f"Bot is LIVE! Force-joining active on {SPONSOR_CHANNEL}")
    app.run_polling()

if __name__ == "__main__":
    main()
