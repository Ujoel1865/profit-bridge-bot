#profit_bridge_bot.py

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

# --- Enhanced Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Delete webhook before polling
try:
    bot.delete_webhook()
    logger.info("🌐 Webhook cleared successfully")
except Exception as e:
    logger.error(f"⚠️ Webhook clearance failed: {e}")

# --- START Command ---
@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    ensure_user_profile(telegram_id, full_name)
    bot.send_message(
        message.chat.id,
        "🌟 *Welcome to ProfitBridge!* 🌟\n\n"
        "Your gateway to seamless crypto management:\n\n"
        "💳 `/deposit` - Get your wallet address\n"
        "📊 `/balance` - Check portfolio value\n"
        "🛠️ `/mint` - Start earning rewards\n"
        "💸 `/withdraw` - Request payout\n\n"
        "🚀 Start your journey with a deposit!",
        parse_mode='Markdown'
    )

# --- DEPOSIT Command ---
@bot.message_handler(commands=['deposit'])
def deposit(message):
    telegram_id = message.from_user.id
    wallet = get_wallet_by_user(telegram_id) or create_wallet_for_user(telegram_id)

    bot.send_message(
        message.chat.id,
        "🔐 *Secure Deposit Address* 🔐\n\n"
        "Send *USDT (TRC20)* or *TRX* to:\n\n"
        f"`{wallet['address']}`\n\n"
        "ℹ️ Funds will appear after 6 network confirmations\n"
        "⚠️ Only send TRC20 assets to this address",
        parse_mode='Markdown'
    )

# --- BALANCE Command ---
@bot.message_handler(commands=['balance'])
def balance(message):
    telegram_id = message.from_user.id
    if not (wallet := get_wallet_by_user(telegram_id)):
        bot.send_message(message.chat.id, "❌ *Wallet not found!*\nUse /deposit to generate one", parse_mode='Markdown')
        return

    try:
        refresh_user_balance(telegram_id)
        updated_wallet = get_wallet_by_user(telegram_id)
        trx = updated_wallet.get("trx_balance", 0)
        usdt = updated_wallet.get("usdt_balance", 0)
        
        bot.send_message(
            message.chat.id,
            "💰 *Portfolio Overview* 💰\n\n"
            f"• 💵 USDT (TRC-20): `{usdt:.2f}`\n"
            f"• 💠 TRX: `{trx:.4f}`\n\n"
            "🔄 Updated in real-time",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Balance error: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ *Service Unavailable*\n\n"
            "Balance retrieval failed. Please try again later",
            parse_mode='Markdown'
        )

# --- MINT Command ---
@bot.message_handler(commands=['mint'])
def mint(message):
    try:
        bot.send_message(
            message.chat.id,
            "⏳ Initializing minting session..."
        )
        handle_mint(update=message, context=None, bot=bot)
    except Exception as e:
        logger.error(f"Mint error: {e}")
        bot.send_message(
            message.chat.id,
            "❌ *Minting Failed*\n\n"
            "System encountered an error. Please:\n\n"
            "1️⃣ Check your balance with /balance\n"
            "2️⃣ Ensure sufficient TRX for gas\n"
            "3️⃣ Try again later",
            parse_mode='Markdown'
        )

# --- WITHDRAW Command ---
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    bot.send_message(
        message.chat.id,
        "📬 *Withdrawal Request Received*\n\n"
        "Our finance team will:\n\n"
        "✅ Verify your balance\n"
        "✅ Process within 24h\n"
        "✅ Notify upon completion\n\n"
        "ℹ️ Minimum withdrawal: $50 USDT",
        parse_mode='Markdown'
    )

# --- Start Polling ---
if __name__ == "__main__":
    logger.info("🤖 ProfitBridge Bot activated")
    logger.info("🔄 Starting polling loop...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=3, timeout=45)
        except Exception as e:
            logger.critical(f"🚨 CRASH: {e}")
            logger.info("⏳ Restarting in 15 seconds...")
            time.sleep(15)
            try:
                bot.delete_webhook()
                logger.info("🌐 Webhook reset")
            except Exception as webhook_err:
                logger.error(f"⚠️ Webhook reset failed: {webhook_err}")
