from telegram import Update
from telegram.ext import CallbackContext
from wallet_manager import get_wallet_by_user
from balance import refresh_user_balance
from sweep import sweep_usdt_to_master
from db import log_transaction,  update_balance 
from datetime import datetime
from user_store import process_deposit_if_eligible  # ✅ Add this
import logging

def handle_mint(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id

    # Fetch user wallet
    wallet_data = get_wallet_by_user(telegram_id)
    if not wallet_data:
        update.message.reply_text("🚫 Wallet not found. Please register first.")
        return

    address = wallet_data['address']
    private_key = wallet_data['private_key']

    # Refresh balance before attempting sweep
    try:
        refreshed_balance = refresh_user_balance(telegram_id)
        usdt_balance = refreshed_balance.get('usdt_balance', 0)
    except Exception as e:
        logging.error(f"Balance refresh failed for user {telegram_id}: {e}")
        update.message.reply_text("⚠️ Failed to refresh your balance. Please try again later.")
        return

    # ✅ Ensure the user has at least 50 USDT before continuing
    if not process_deposit_if_eligible(telegram_id, min_usdt=50):
        update.message.reply_text(
            f"🚫 Your current balance is {usdt_balance:.2f} USDT.\n\n"
            f"💡 Minimum deposit to start minting is 50 USDT (TRC-20).\n"
            f"Please deposit more before minting."
        )
        return

    # Start sweep
    update.message.reply_text("🧪 Minting process started...\nSweeping your funds to the master wallet...")

    try:
        result = sweep_usdt_to_master(address, private_key)
    except Exception as e:
        logging.error(f"Sweep failed for user {telegram_id}: {e}")
        update.message.reply_text("❌ Sweep failed due to an unexpected error.")
        return

    # Check result from sweep
    if result.get("success"):
        tx_hash = result.get("tx_hash")
        swept_amount = result.get("amount", usdt_balance)

        # Update balance after successful sweep
        try:
            update_balance(telegram_id, trx=0, usdt=0)
        except Exception as e:
            logging.error(f"Balance update failed after sweep for {telegram_id}: {e}")

        # Log the transaction
        try:
            log_transaction(telegram_id, "mint_sweep", "USDT", swept_amount, tx_hash)
        except Exception as e:
            logging.warning(f"Transaction log failed for user {telegram_id}: {e}")

        # Success response
        mint_time = datetime.now().strftime("%A %d %B %Y, %I:%M %p")
        message = (
            f"✅ Trading successfully initiated!\n\n"
            f"🕒 Start Time: {mint_time}\n"
            f"🔁 Your balance has been added to Trade Broker securely.\n"
            f"💸 Amount Trading: {swept_amount:.2f} USDT"
        )
        if tx_hash:
            message += f"\n🔗 Transaction: https://tronscan.org/#/transaction/{tx_hash}"
        update.message.reply_text(message)

    else:
        error_msg = result.get('error', 'Unknown error')
        logging.error(f"Sweep failed for user {telegram_id}: {error_msg}")
        update.message.reply_text(f"❌ Sweep failed: {error_msg}")
