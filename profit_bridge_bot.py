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

# --- Optional Logging ---
logging.basicConfig(level=logging.INFO)

# Delete webhook before polling
try:
    bot.delete_webhook()
    print("✅ Webhook deleted successfully")
except Exception as e:
    print(f"❌ Webhook deletion failed: {e}")

# --- START Command ---
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    # ✅ Ensure wallet is created and stored
    ensure_user_profile(telegram_id, full_name)
    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Profit_Bridge*!\n\n"
        "💰 Use /deposit to get your wallet address\n"
        "📊 Use /balance to check your portfolio\n"
        "⚒️ Use /mint to start minting (after deposit)\n"
        "💸 Use /withdraw to request payout",
        parse_mode='Markdown'
    )

# --- DEPOSIT Command ---
@bot.message_handler(commands=['deposit'])
def deposit(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id)

    if not wallet:
        wallet = create_wallet_for_user(telegram_id)

    bot.send_message(
        message.chat.id,
        f"🔐 Your deposit wallet (TRC20):\n\n"
        f"`{wallet['address']}`\n\n"
        f"💡 You can send USDT (TRC20) or TRX to this address.",
        parse_mode='Markdown'
    )

# --- BALANCE Command ---
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
        trx, usdt = updated_wallet.get("trx_balance", 0), updated_wallet.get("usdt_balance", 0)

        bot.send_message(
            message.chat.id,
            f"💼 Your Wallet Balance:\n\n"
            f"💵 *USDT (TRC-20)*: {usdt:.2f} USDT\n"
            f"💰 *TRX*: {trx:.4f} TRX",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error fetching balance: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to retrieve balance. Please try again later.")

# --- MINT Command ---
@bot.message_handler(commands=['mint'])
def mint(message):
    try:
        handle_mint(update=message, context=None, bot=bot)
    except Exception as e:
        logging.error(f"Mint command error: {e}")
        bot.send_message(message.chat.id, "❌ Mint failed. Please try again later.")

# --- WITHDRAW Command (Manual) ---
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    bot.send_message(
        message.chat.id,
        "🚨 Withdrawal request received!\n"
        "Our team will verify your balance and process your payment manually."
    )


