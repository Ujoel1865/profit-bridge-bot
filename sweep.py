# sweep.py

import time
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider

from wallet_manager import get_wallet_by_user, get_wallet_balances
from db import log_transaction, update_balance
from config import (
    TRONGRID_API_KEY,
    MASTER_WALLET_ADDRESS,
    MASTER_WALLET_PRIVATE_KEY,
    USDT_CONTRACT_ADDRESS
)

MIN_USDT_FOR_SWEEP = 45
TRX_TOPUP_AMOUNT = 1_100_000  # 1.1 TRX in sun (TRX has 6 decimals)
SWEEP_TRIALS = 4
WAIT_INTERVAL = 8 * 60  # 8 minutes in seconds


def initialize_tron_client():
    return Tron(
        provider=HTTPProvider(endpoint_uri="https://api.trongrid.io", api_key=TRONGRID_API_KEY),
        network="mainnet"
    )


def send_trx_to_user(client, to_address):
    print(f"💸 Sending 1.1 TRX to {to_address} from master...")
    master_key = PrivateKey(bytes.fromhex(MASTER_WALLET_PRIVATE_KEY))
    try:
        txn = (
            client.trx.transfer(MASTER_WALLET_ADDRESS, to_address, TRX_TOPUP_AMOUNT)
            .memo("TRX for sweep")
            .fee_limit(1_000_000)
            .build()
            .sign(master_key)
            .broadcast()
        )
        txn.wait()
        print("✅ TRX sent to user wallet.")
        return True
    except Exception as e:
        print(f"❌ Failed to send TRX: {str(e)}")
        return False


def sweep_usdt_to_master(telegram_id):
    client = initialize_tron_client()

    wallet = get_wallet_by_user(telegram_id)
    if not wallet:
        print("❌ User wallet not found.")
        return {
            "success": False,
            "error": "⚠️ Wallet not found. Please register first."
        }

    address = wallet['address']
    private_key = wallet['private_key']
    user_key = PrivateKey(bytes.fromhex(private_key))

    # Step 1: Check user balance
    trx, usdt = get_wallet_balances(address)
    update_balance(telegram_id, trx, usdt)

    if usdt < MIN_USDT_FOR_SWEEP:
        return {
            "success": False,
            "error": f"⚠️ Your balance is {usdt:.2f} USDT. Minimum required: {MIN_USDT_FOR_SWEEP}."
        }

    if trx < 1.1:
        print("🚫 Insufficient TRX. Topping up user wallet...")

        if not send_trx_to_user(client, address):
            return {
                "success": False,
                "error": "❌ Could not fund TRX for transaction fee."
            }

        for attempt in range(SWEEP_TRIALS):
            print(f"⏳ Waiting for TRX to arrive (attempt {attempt + 1}/4)...")
            time.sleep(WAIT_INTERVAL)
            trx, _ = get_wallet_balances(address)
            update_balance(telegram_id, trx, usdt)
            if trx >= 1.1:
                print("✅ TRX top-up confirmed.")
                break
        else:
            return {
                "success": False,
                "error": "⚠️ Still no TRX after multiple attempts. Try again later."
            }

    # Step 2: Sweep USDT
    try:
        contract = client.get_contract(USDT_CONTRACT_ADDRESS)
        balance = contract.functions.balanceOf(address)
        usdt_amount = balance / 1_000_000

        print(f"💵 Sweeping {usdt_amount:.2f} USDT from {address} to master wallet...")

        txn = (
            contract.functions.transfer(MASTER_WALLET_ADDRESS, balance)
            .with_owner(address)
            .fee_limit(5_000_000)
            .build()
            .sign(user_key)
            .broadcast()
        )

        result = txn.wait()
        txid = result.get('txid')
        print(f"✅ Sweep complete. TXID: {txid}")

        log_transaction(telegram_id, "sweep", "USDT", usdt_amount, txid)

        return {
            "success": True,
            "tx_hash": txid,
            "amount": usdt_amount
        }

    except Exception as e:
        print(f"❌ Sweep failed: {str(e)}")
        return {
            "success": False,
            "error": "❌ Failed to sweep USDT. Please try again later."
        }
