# deposit_checker.py

import time
from tronpy import Tron
from tronpy.providers import HTTPProvider

from config import TRONGRID_API_KEY, USDT_CONTRACT_ADDRESS
from wallet_manager import get_wallet_by_user, get_wallet_balances
from db import get_connection, update_balance, log_transaction

MIN_USDT_DEPOSIT = 50

def initialize_tron_client():
    return Tron(
        provider=HTTPProvider(endpoint_uri="https://api.trongrid.io", api_key=TRONGRID_API_KEY),
        network="mainnet"
    )

def get_all_user_ids():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM users;")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [row['telegram_id'] for row in results]

def check_and_log_deposits():
    print("📡 Deposit Checker Started (via tronpy)...\n")
    client = initialize_tron_client()

    user_ids = get_all_user_ids()
    if not user_ids:
        print("🚫 No users found.")
        return

    for user_id in user_ids:
        wallet = get_wallet_by_user(user_id)
        if not wallet:
            print(f"❌ Wallet not found for user {user_id}")
            continue

        address = wallet['address']
        print(f"🔍 Checking user {user_id} @ {address}")

        try:
            trx, usdt = get_wallet_balances(address)
        except Exception as e:
            print(f"❌ Error fetching balance for {address}: {e}")
            continue

        print(f"💰 TRX Balance: {trx:.6f} TRX")
        print(f"💵 USDT Balance: {usdt:.6f} USDT")

        # ✅ Always update balance, even if below threshold
        update_balance(user_id, trx, usdt)

        if usdt >= MIN_USDT_DEPOSIT:
            log_transaction(user_id, "deposit", "USDT", usdt)
            print(f"✅ Deposit logged for user {user_id} ({usdt:.2f} USDT)\n")
        else:
            print(f"⚠️ Balance updated, but not a valid deposit yet (user {user_id} has {usdt:.2f} USDT)\n")

if __name__ == "__main__":
    while True:
        check_and_log_deposits()
        print("⏳ Waiting before next check...\n")
        time.sleep(30)  # You can increase to 60+ for production
