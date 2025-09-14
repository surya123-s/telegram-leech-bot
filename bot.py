# bot.py
import os
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------- Configuration from env ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")  # comma separated user ids
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", str(2 * 1024**3)))  # default 2GB

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in environment variables")

ALLOWED_USERS = {int(x) for x in ALLOWED_USERS.split(",") if x.strip()}

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("leech-bot")

# ---------- Pyrogram client ----------
app = Client("leechbot", bot_token=BOT_TOKEN)

# Semaphore to limit concurrent downloads
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

async def run_yt_dlp(url: str, output_dir: Path) -> Path:
    """
    Run yt-dlp to download the best video/audio and return resulting filepath.
    """
    # output template
    out_template = str(output_dir / "%(title).200s.%(ext)s")
    cmd = ["yt-dlp", "-f", "best", "-o", out_template, url, "--no-playlist", "--merge-output-format", "mp4"]
    logger.info("Running yt-dlp: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error("yt-dlp failed: %s", stderr.decode(errors="ignore")[:1000])
        raise RuntimeError("yt-dlp failed: " + stderr.decode(errors="ignore"))

    # pick largest file in output_dir
    files = list(output_dir.iterdir())
    if not files:
        raise RuntimeError("No file produced by yt-dlp")
    biggest = max(files, key=lambda p: p.stat().st_size)
    logger.info("Downloaded file: %s (%d bytes)", biggest.name, biggest.stat().st_size)
    return biggest

def allowed_or_reply(func):
    async def wrapper(client, message: Message):
        if ALLOWED_USERS and message.from_user and message.from_user.id not in ALLOWED_USERS:
            await message.reply_text("You are not authorized to use this bot.")
            return
        return await func(client, message)
    return wrapper

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await message.reply_text("Hello — send /leech <URL> to download and upload video.")

@app.on_message(filters.command("leech") & filters.private)
@allowed_or_reply
async def leech_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /leech <url>")
        return
    url = message.command[1]
    user = message.from_user
    await message.reply_text(f"Queued download: {url}")

    # schedule download/upload
    asyncio.create_task(process_leech(message, url))

async def process_leech(message: Message, url: str):
    # Acquire semaphore
    async with download_semaphore:
        msg = await message.reply_text("Starting download...")
        try:
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                filepath = await run_yt_dlp(url, td_path)
                filesize = filepath.stat().st_size
                if filesize > MAX_FILE_SIZE_BYTES:
                    await msg.edit_text(f"File too large: {filesize} bytes (> {MAX_FILE_SIZE_BYTES}). Aborting.")
                    return
                await msg.edit_text(f"Uploading {filepath.name} ({filesize//1024} KB)...")

                # send as document (use chunking by Pyrogram automatically)
                async with filepath.open("rb") as f:
                    await message.reply_document(document=f, file_name=filepath.name, caption=f"Leech: {filepath.name}")
                await msg.edit_text("Upload complete.")
        except Exception as e:
            logger.exception("Error in leech pipeline")
            await message.reply_text(f"Error: {e}")

if __name__ == "__main__":
    # Start the bot
    logger.info("Starting Pyrogram client")
    app.run()
