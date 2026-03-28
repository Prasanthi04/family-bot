"""
Family Telegram Bot — main entry point.
Uses python-telegram-bot in polling mode (no webhook/server needed).
Run with: python -m app.main
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from .bot import handle_message

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ── /start command ────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your family assistant bot.\n"
        "Use /bot followed by your question. Examples:\n\n"
        "/bot plan a 3-day trip to San Diego in July\n"
        "/bot remind everyone to pack by Friday\n"
        "/bot what should we pack for a beach trip?"
    )


# ── /bot trigger ─────────────────────────────────────────────────────────────
async def cmd_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    sender_id   = str(update.effective_user.id)
    sender_name = update.effective_user.first_name or "Someone"

    if not query:
        await update.message.reply_text(
            "What would you like help with? Try:\n"
            "/bot plan a weekend trip to Las Vegas"
        )
        return

    # Show typing indicator while Claude thinks
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    reply = await handle_message(
        sender_id=sender_id,
        sender_name=sender_name,
        query=query,
    )
    await update.message.reply_text(reply)


# ── Ignore everything else (no accidental replies) ────────────────────────────
async def ignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


# ── App bootstrap ─────────────────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("bot",   cmd_bot))
    app.add_handler(MessageHandler(filters.ALL, ignore))

    log.info("Bot is running — send /bot in your Telegram group!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
