# wallet_monitor.py

import time
import logging
import threading
from datetime import datetime
from balance import refresh_user_balance
from db import get_connection
from config import ADMIN_USER_ID
from telebot import TeleBot

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300  # 5 minutes
HEARTBEAT_INTERVAL_SECONDS = 10800  # 3 hours

bot = None  

def configure_bot_instance(bot_instance):
    global bot
    bot = bot_instance


def get_all_wallets():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT telegram_id, wallet_address FROM users")
        users = cur.fetchall()
        cur.close()
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error fetching wallets from DB: {e}")
        return []



def send_admin_alert(wallet_info, trx, usdt):
    telegram_id = wallet_info.get("telegram_id")
    address = wallet_info.get("wallet_address")

    msg = (
        f"⚠️ *Low USDT Balance Alert*\n\n"
        f"🆔 Telegram ID: `{telegram_id}`\n"
        f"🔐 Wallet Address: `{address}`\n"
        f"💵 USDT Balance: `{usdt:.4f}`\n"
        f"💰 TRX Balance: `{trx:.4f}`\n"
        f"⏰ Checked at: {datetime.now().isoformat()}"
    )
    try:
        bot.send_message(ADMIN_USER_ID, msg, parse_mode="Markdown")
        logger.info(f"Alert sent for wallet {address} (user {telegram_id})")
    except Exception as e:
        logger.error(f"Failed to send alert for wallet {address}: {e}")


def monitor_loop():
    logger.info("Wallet Monitor started.")
    first_run = True  # Track the first iteration

    while True:
        try:
            wallets = get_all_wallets()
            logger.info(f"Checking {len(wallets)} wallets...")

            for wallet in wallets:
                telegram_id = wallet.get("telegram_id")
                try:
                    balances = refresh_user_balance(telegram_id)
                    trx = balances["trx_balance"]
                    usdt = balances["usdt_balance"]
                    logger.info(f"User {telegram_id} wallet balance: TRX={trx:.4f}, USDT={usdt:.4f}")

                    # First run: alert all
                    # Later: alert only if USDT > 10
                    if first_run or usdt > 10:
                        send_admin_alert(wallet, trx, usdt)

                except Exception as e:
                    logger.error(f"Error refreshing balance for user {telegram_id}: {e}")

        except Exception as e:
            logger.error(f"Error in wallet monitor main loop: {e}")

        first_run = False  # Mark that the first run is complete
        time.sleep(CHECK_INTERVAL_SECONDS)



def start_monitoring_in_thread():
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    logger.info("Wallet Monitor thread started.")


def send_heartbeat():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            heartbeat_msg = f"🟢 *Wallet Monitor Active*\nLast ping: `{now}`"
            bot.send_message(ADMIN_USER_ID, heartbeat_msg, parse_mode="Markdown")
            logger.info("Sent heartbeat message to admin.")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


def start_heartbeat_in_thread():
    thread = threading.Thread(target=send_heartbeat, daemon=True)
    thread.start()
    logger.info("Heartbeat thread started.")
