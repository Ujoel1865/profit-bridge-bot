# user_store.py

from wallet_manager import generate_tron_wallet, get_wallet_by_user, save_wallet, get_wallet_balances
from db import create_user, get_wallet, update_balance, log_transaction

def ensure_user_profile(telegram_id, full_name=None):
    """
    Ensures the user is registered with a wallet.
    If not, generate and save one. Optionally logs full_name.
    Returns wallet_address.
    """
    wallet = get_wallet_by_user(telegram_id)

    if wallet:
        return wallet['address']

    new_wallet = generate_tron_wallet()
    save_wallet(telegram_id, new_wallet)
    create_user(telegram_id, new_wallet['address'], new_wallet['private_key'])

    # Optional: Save full_name if your DB supports it
    return new_wallet['address']


def refresh_user_balance(telegram_id):
    """
    Check on-chain wallet balance and update DB.
    """
    wallet_address = get_wallet_by_user(telegram_id)
    if not wallet_address:
        print(f"❌ No wallet found for {telegram_id}")
        return

    trx, usdt = get_wallet_balances(wallet_address['address'])
    update_balance(telegram_id, trx, usdt)
    print(f"✅ Updated balance for {telegram_id}: TRX={trx:.6f}, USDT={usdt:.6f}")


def process_deposit_if_eligible(telegram_id, min_usdt=50):
    """
    Check if user has deposited at least `min_usdt`.
    If yes, update balance and log deposit.
    Returns True if deposit is valid, False otherwise.
    """
    wallet_address = get_wallet_by_user(telegram_id)
    if not wallet_address:
        return False

    _, usdt = get_wallet_balances(wallet_address['address'])
    if usdt >= min_usdt:
        update_balance(telegram_id, 0, usdt)
        log_transaction(telegram_id, "deposit", "USDT", usdt)
        return True
    return False


def get_user_wallet_address(telegram_id):
    wallet = get_wallet_by_user(telegram_id)
    return wallet['address'] if wallet else None
