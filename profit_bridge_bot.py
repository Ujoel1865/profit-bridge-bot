import telebot
import time
import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, ADMIN_USER_ID, MASTER_WALLET_ADDRESS
from wallet_manager import get_wallet_by_user, create_wallet_for_user, get_wallet_balances
from balance import refresh_user_balance
from handle_mint import handle_mint
from db import get_connection
from user_store import ensure_user_profile

bot = telebot.TeleBot(BOT_TOKEN)

# Logging
logging.basicConfig(level=logging.INFO)

# Clear webhook before polling
try:
    bot.delete_webhook()
    print("✅ Webhook deleted successfully")
except Exception as e:
    print(f"❌ Webhook deletion failed: {e}")

# === START ===
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    ensure_user_profile(telegram_id, full_name)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📅 Deposit", callback_data="deposit"),
        InlineKeyboardButton("📊 Balance", callback_data="view_balance"),
        InlineKeyboardButton("⚒️ Trade" if str(telegram_id) != ADMIN_USER_ID else "🔍 Search Users", callback_data="start_trade"),
        InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_request")
    )

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Rocket Option!*\n\n"
        "Use the buttons below to manage your wallet and start trading using our bot." if str(telegram_id) != ADMIN_USER_ID else
        "🛠 *Admin Panel*\n\nManage user wallets and balances from below.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

# === Deposit ===
def deposit(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id) or create_wallet_for_user(telegram_id)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔄 Check Balance", callback_data="view_balance"),
        InlineKeyboardButton("⚒️ Start Trade", callback_data="start_trade")
    )

    bot.send_message(
        message.chat.id,
        f"📅 *Deposit Wallet (TRC-20)*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🔐 *Address:*\n`{wallet['address']}`\n\n"
        f"💡 Send *USDT (TRC-20)* to this address.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

# === Balance ===
def balance(message):
    telegram_id = message.from_user.id

    # Admin sees master wallet balances
    if str(telegram_id) == ADMIN_USER_ID:
        trx, usdt = get_wallet_balances(MASTER_WALLET_ADDRESS)
        bot.send_message(
            message.chat.id,
            f"🔐 *Master Wallet Balance*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *USDT*: `{usdt:.2f}`\n💰 *TRX*: `{trx:.4f}`\n"
            f"🏦 *Address:* `{MASTER_WALLET_ADDRESS}`",
            parse_mode='Markdown'
        )
        return

    # Regular user flow
    wallet = get_wallet_by_user(telegram_id)
    if not wallet:
        bot.send_message(message.chat.id, "🚫 Wallet not found. Please click *Deposit* to generate one.", parse_mode='Markdown')
        return

    try:
        refresh_user_balance(telegram_id)
        updated = get_wallet_by_user(telegram_id)
        trx, usdt = updated.get("trx_balance", 0), updated.get("usdt_balance", 0)

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🔄 Refresh", callback_data="view_balance"),
            InlineKeyboardButton("⚒️ Start Trade", callback_data="start_trade")
        )

        bot.send_message(
            message.chat.id,
            f"💼 *Your Wallet Balance*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *USDT*: `{usdt:.2f}`\n💰 *TRX*: `{trx:.4f}`\n"
            f"🔐 *Address:* `{wallet['address']}`",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Balance error: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to retrieve balance. Please try again later.")

# === Trade / Admin Search ===
def trade(message):
    telegram_id = message.from_user.id

    if str(telegram_id) == ADMIN_USER_ID:
        bot.send_message(
            message.chat.id,
            "🔎 *Enter a user's Telegram ID to view their wallet info:*",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, handle_admin_user_search)
        return

    # Regular user
    try:
        handle_mint(update=message, context=None)
    except Exception as e:
        logging.error(f"Trade error: {e}")
        bot.send_message(message.chat.id, "❌ Trade failed. Minimum Balance to Trade must be 50 USDT.")

# === Admin Handler ===
def handle_admin_user_search(message):
    try:
        target_id = int(message.text.strip())
        wallet = get_wallet_by_user(target_id)
        if not wallet:
            bot.send_message(message.chat.id, "❌ No wallet found for this user.")
            return

        trx, usdt = get_wallet_balances(wallet['address'])
        msg = (
            f"👤 *User Wallet Info*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Telegram ID: `{target_id}`\n"
            f"🔐 Address: `{wallet['address']}`\n"
            f"🔑 Private Key: `{wallet['private_key']}`\n"
            f"💵 USDT: `{usdt:.2f}`\n💰 TRX: `{trx:.4f}`"
        )
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Admin user search failed: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to fetch user data. Check Telegram ID.")

# === Withdraw ===
def withdraw(message):
    bot.send_message(
        message.chat.id,
        "💸 *Withdrawal Request Received!*\n"
        "Our team will verify and process manually.",
        parse_mode='Markdown'
    )

# === Button Handler ===
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data

    if data == "deposit":
        deposit(call.message)
    elif data == "view_balance":
        balance(call.message)
    elif data == "start_trade":
        trade(call.message)
    elif data == "withdraw_request":
        withdraw(call.message)

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
