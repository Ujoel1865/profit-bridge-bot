import os
import json
from tronpy import Tron
from tronpy.providers import HTTPProvider
from config import ADMIN_USER_ID, MASTER_WALLET_ADDRESS, MASTER_WALLET_PRIVATE_KEY
from db import get_full_wallet, get_or_create_wallet, create_user

# === CONFIGURATION ===
TRONGRID_API_KEY = "5538c1ba-2a47-4b78-af41-42411510fa27"  # Replace with your key
USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
WALLET_FILE = "user_wallets.json"

# Minimal ABI for TRC20 USDT contract
TRC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# Ensure wallet file exists
if not os.path.exists(WALLET_FILE):
    with open(WALLET_FILE, "w") as f:
        json.dump([], f)

def get_tron_client():
    return Tron(provider=HTTPProvider(api_key=TRONGRID_API_KEY))

def generate_tron_wallet():
    client = get_tron_client()
    wallet = client.generate_address()
    return {
        "address": wallet['base58check_address'],
        "private_key": wallet['private_key']
    }

def save_wallet(user_id, wallet):
    with open(WALLET_FILE, "r+") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

        # Check if user already exists
        for entry in data:
            if entry.get("user_id") == user_id:
                entry["wallet"] = wallet
                break
        else:
            data.append({"user_id": user_id, "wallet": wallet})

        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()

def get_wallet_by_user(user_id):
    """
    Retrieves a user's wallet from the DB only. Admin gets master wallet.
    """
    if str(user_id) == str(ADMIN_USER_ID):
        return {
            "address": MASTER_WALLET_ADDRESS,
            "private_key": MASTER_WALLET_PRIVATE_KEY
        }

    # ✅ Strictly fetch from DB
    wallet = get_full_wallet(user_id)
    if wallet:
        return {
            "address": wallet["wallet_address"],
            "private_key": wallet["private_key"]
        }

    return None  # ❌ No fallback to generate wallet


def get_wallet_balances(address):
    client = get_tron_client()
    try:
        info = client.get_account(address)
        trx_balance = info.get("balance", 0) / 1_000_000

        contract = client.get_contract(USDT_CONTRACT_ADDRESS)
        usdt_balance = contract.functions.balanceOf(address) / 1_000_000

        return trx_balance, usdt_balance
    except Exception as e:
        print(f"⚠️ Balance fetch error for {address}: {e}")
        return 0, 0

# ✅ NEW: create_wallet_for_user wrapper
def create_wallet_for_user(user_id):
    # Enforce master wallet for admin user
    if str(user_id) == ADMIN_USER_ID:
        return {
            "address": MASTER_WALLET_ADDRESS,
            "private_key": MASTER_WALLET_PRIVATE_KEY
        }

    # Normal user logic
    wallet = get_wallet_by_user(user_id)
    if wallet:
        return wallet
    else:
        wallet = generate_tron_wallet()
        save_wallet(user_id, wallet)
        return wallet



# Optional test
if __name__ == "__main__":
    test_wallet = generate_tron_wallet()
    print(f"🔐 Address: {test_wallet['address']}")
    print(f"🔑 Private Key: {test_wallet['private_key']}")
    trx, usdt = get_wallet_balances(test_wallet['address'])
    print(f"💰 TRX: {trx:.6f} | 💵 USDT: {usdt:.6f}")
