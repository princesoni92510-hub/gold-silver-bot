"""
bot.py
------
Telegram bot that:
- Asks for gold/silver prices every day at 8 PM IST
- Parses reply, saves to data.json
- Generates posters for ALL templates in /templates folder
- Sends every poster back to Telegram with shop name caption
"""

import json
import logging
from datetime import datetime, time
from pathlib import Path

import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from poster_gen import generate_all_posters

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BASE_DIR  = Path(__file__).parent
DATA_JSON = BASE_DIR / "data.json"

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  SEND DAILY PROMPT
# ─────────────────────────────────────────────

async def ask_for_prices(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data if context.job else context._chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🪙 *Aaj ka Bhaav bhejo!*\n\n"
            "Reply in this exact format:\n\n"
            "`GOLD24: 72000`\n"
            "`GOLD22: 66000`\n"
            "`SILVER: 85`"
        ),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
#  COMMAND: /start
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Namaste! I'm your Bhaav Bot.\n\n"
        f"Your Chat ID is: `{chat_id}`\n\n"
        f"📅 I will ask for prices every day at *8:00 PM IST*.\n\n"
        f"Send /bhaav anytime to test manually.",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
#  COMMAND: /bhaav  (manual test)
# ─────────────────────────────────────────────

async def cmd_bhaav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context._chat_id = update.effective_chat.id
    context.job = None
    await ask_for_prices(context)

# ─────────────────────────────────────────────
#  GENERATE POSTERS + SEND TO TELEGRAM
# ─────────────────────────────────────────────

async def generate_and_send(bot, chat_id: int, prices: dict):
    generated = generate_all_posters(prices)

    if not generated:
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ No templates found in /templates folder.\nAdd .html files there to generate posters."
        )
        return

    await bot.send_message(
        chat_id=chat_id,
        text=f"✅ Generated {len(generated)} poster(s)! Sending now..."
    )

    for caption, image_path in generated:
        try:
            with open(str(image_path), "rb") as img:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=img,
                    caption=f"🖼️ *{caption}*",
                    parse_mode="Markdown"
                )
            log.info(f"Sent poster: {caption}")
        except Exception as e:
            log.error(f"Failed to send {caption}: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Could not send *{caption}*: {e}",
                parse_mode="Markdown"
            )

# ─────────────────────────────────────────────
#  MESSAGE HANDLER — parse prices and process
# ─────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text    = update.message.text.strip()
    chat_id = update.effective_chat.id
    prices  = {}

    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key   = key.strip().upper()
        value = value.strip().replace(",", "")

        if key == "GOLD24":
            prices["gold_24"] = value
        elif key == "GOLD22":
            prices["gold_22"] = value
        elif key == "SILVER":
            prices["silver"] = value

    # Validate
    if len(prices) < 3:
        await update.message.reply_text(
            "⚠️ Format sahi nahi tha. Please send exactly:\n\n"
            "GOLD24: 72000\n"
            "GOLD22: 66000\n"
            "SILVER: 85"
        )
        return

    prices["date"] = datetime.now().strftime("%d-%m-%Y")

    # Save to data.json
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(prices, f, indent=2, ensure_ascii=False)
    log.info(f"Saved data.json: {prices}")

    # Confirm receipt
    await update.message.reply_text(
        f"✅ *Prices saved!*\n\n"
        f"Gold 24K : ₹{prices['gold_24']}\n"
        f"Gold 22K : ₹{prices['gold_22']}\n"
        f"Silver    : ₹{prices['silver']}\n\n"
        f"🖨️ Generating posters, please wait...",
        parse_mode="Markdown"
    )

    # Generate all posters and send back
    await generate_and_send(context.bot, chat_id, prices)

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    # Convert chat ID safely
    chat_id = int(CHAT_ID)

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("bhaav", cmd_bhaav))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    # India timezone
    ist = pytz.timezone("Asia/Kolkata")

    # Daily reminder at 8 PM IST
    app.job_queue.run_daily(
        callback=ask_for_prices,
        time=time(hour=20, minute=0, tzinfo=ist),
        data=chat_id,
        name="daily_bhaav_request",
    )

    log.info("✅ Daily job scheduled at 8:00 PM IST")

    print("\n✅ Bot is running! Press Ctrl+C to stop.\n")

    app.run_polling()


if __name__ == "__main__":
    main()