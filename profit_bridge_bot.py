# === PROFIT_BRIDGE_BOT.PY ===

import telebot
import time
import logging
from config import BOT_TOKEN
from wallet_manager import get_wallet_by_user, create_wallet_for_user
from balance import refresh_user_balance
from handle_mint import handle_mint
from db import get_connection
from user_store import ensure_user_profile

bot = telebot.TeleBot(BOT_TOKEN)

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)

# === Remove Webhook (for polling mode) ===
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
    ensure_user_profile(telegram_id, full_name)

    welcome_msg = (
        "👋 *Welcome to Profit Bridge Bot!*\n\n"
        "Manage your wallet and trade using the options below:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 /deposit — Get your deposit wallet address\n"
        "📊 /balance — View your USDT & TRX balance\n"
        "📈 /trade — Execute a smart trade (after deposit)\n"
        "💸 /withdraw — Request manual withdrawal"
    )
    bot.send_message(message.chat.id, welcome_msg, parse_mode='Markdown')

# === DEPOSIT Command ===
@bot.message_handler(commands=['deposit'])
def deposit(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id)

    if not wallet:
        wallet = create_wallet_for_user(telegram_id)

    deposit_msg = (
        f"📥 *Your Deposit Wallet (TRC-20)*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"`{wallet['address']}`\n\n"
        f"💡 You can send *USDT (TRC-20)* or *TRX* to this address.\n"
        f"⏳ Funds will reflect shortly after confirmation."
    )
    bot.send_message(message.chat.id, deposit_msg, parse_mode='Markdown')

# === BALANCE Command ===
@bot.message_handler(commands=['balance'])
def balance(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id)

    if not wallet:
        bot.send_message(message.chat.id, "🚫 Wallet not found. Use /deposit to generate one.")
        return

    try:
        refresh_user_balance(telegram_id)
        updated_wallet = get_wallet_by_user(telegram_id)
        trx = updated_wallet.get("trx_balance", 0)
        usdt = updated_wallet.get("usdt_balance", 0)

        balance_msg = (
            "📊 *Wallet Summary*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *USDT*: `{usdt:.2f}` USDT\n"
            f"💰 *TRX*: `{trx:.4f}` TRX\n"
            f"🔐 Address:\n`{wallet['address']}`"
        )
        bot.send_message(message.chat.id, balance_msg, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Balance error: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to fetch balance. Please try again later.")

# === TRADE Command (was Mint) ===
@bot.message_handler(commands=['trade'])
def trade(message):
    try:
        handle_mint(update=message, context=None, bot=bot)
    except Exception as e:
        logging.error(f"Trade error: {e}")
        bot.send_message(message.chat.id, "❌ Trade failed. Please try again later.")

# === WITHDRAW Command ===
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    withdraw_msg = (
        "💸 *Withdrawal Request Received!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Our admin team will verify your balance and process the payout manually.\n"
        "⏳ Expect confirmation shortly."
    )
    bot.send_message(message.chat.id, withdraw_msg, parse_mode='Markdown')

# === Start Polling ===
print("🤖 Profit_Bridge Bot is live... Press Ctrl+C to stop.")
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
