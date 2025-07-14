# profit_bridge_bot.py

import telebot
import time
import logging
from config import BOT_TOKEN
from wallet_manager import get_wallet_by_user, create_wallet_for_user
from balance import refresh_user_balance
from handle_mint import handle_mint
from db import get_connection
from user_store import ensure_user_profile   # ✅ Correct function

bot = telebot.TeleBot(BOT_TOKEN)

# Optional Logging
logging.basicConfig(level=logging.INFO)

# Delete webhook before polling
try:
    bot.delete_webhook()
    print("✅ Webhook deleted successfully")
except Exception as e:
    print(f"❌ Webhook deletion failed: {e}")

# === START Command ===
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    # Ensure wallet is created and user is registered
    ensure_user_profile(telegram_id, full_name)

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Rocket_Option!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💼 _Your all-in-one crypto automation bot._\n\n"
        "▶️ Available Commands:\n"
        "📥 `/deposit` – Get your wallet address\n"
        "📊 `/balance` – View wallet balance\n"
        "⚒️ `/Trade` – Start Trade Bot (after deposit)\n"
        "💸 `/withdraw` – Request payout\n\n"
        "🛡️ _Secure. Fast. Reliable._",
        parse_mode='Markdown'
    )

# === DEPOSIT Command ===
@bot.message_handler(commands=['deposit'])
def deposit(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id)

    if not wallet:
        wallet = create_wallet_for_user(telegram_id)

    bot.send_message(
        message.chat.id,
        "📥 *Your Deposit Wallet*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔐 Address:\n"
        f"`{wallet['address']}`\n\n"
        "💡 *Supported:* USDT (TRC20) or TRX\n"
        "⚠️ Ensure you send only compatible tokens to avoid loss.",
        parse_mode='Markdown'
    )

# === BALANCE Command ===
@bot.message_handler(commands=['balance'])
def balance(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id)

    if not wallet:
        bot.send_message(message.chat.id, "🚫 *Wallet not found!*\nUse `/deposit` to generate your wallet.", parse_mode='Markdown')
        return

    try:
        refresh_user_balance(telegram_id)
        updated_wallet = get_wallet_by_user(telegram_id)
        trx, usdt = updated_wallet.get("trx_balance", 0), updated_wallet.get("usdt_balance", 0)

        bot.send_message(
            message.chat.id,
            "📊 *Wallet Overview*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *USDT (TRC20)*: `{usdt:.2f}`\n"
            f"💰 *TRX*: `{trx:.4f}`\n\n"
            f"🔐 Address: `{wallet['address']}`",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error fetching balance: {e}")
        bot.send_message(message.chat.id, "⚠️ *Balance retrieval failed.* Please try again later.", parse_mode='Markdown')

# === MINT Command ===
@bot.message_handler(commands=['mint'])
def mint(message):
    try:
        handle_mint(update=message, context=None, bot=bot)
    except Exception as e:
        logging.error(f"Mint command error: {e}")
        bot.send_message(message.chat.id, "❌ *Linking To Trade Bot failed.* Please try again shortly.", parse_mode='Markdown')

# === WITHDRAW Command (Manual) ===
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    bot.send_message(
        message.chat.id,
        "💸 *Withdrawal Request Submitted!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Our team will verify and process your payment shortly.\n"
        "⏳ Please allow up to 24 hours.",
        parse_mode='Markdown'
    )

# === Start Polling ===
print("🤖 Profit_Bridge Bot is running... Press Ctrl+C to stop.")
while True:
    try:
        bot.polling(none_stop=True, interval=2, timeout=30)
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        print("🔄 Restarting in 15 seconds...")
        time.sleep(15)
        try:
            bot.delete_webhook()
            print("✅ Webhook cleared before restart")
        except Exception as webhook_err:
            print(f"⚠️ Webhook reset failed: {webhook_err}")
