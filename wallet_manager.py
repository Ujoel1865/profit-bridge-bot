from tronpy import Tron
from tronpy.providers import HTTPProvider
from db import create_user, get_wallet, update_balance  # ⬅️ DB functions
from decimal import Decimal

# === CONFIGURATION ===
TRONGRID_API_KEY = "5538c1ba-2a47-4b78-af41-42411510fa27"
USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# TRC20 ABI
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

def get_tron_client():
    return Tron(provider=HTTPProvider(api_key=TRONGRID_API_KEY))

def generate_tron_wallet():
    client = get_tron_client()
    wallet = client.generate_address()
    return {
        "address": wallet['base58check_address'],
        "private_key": wallet['private_key']
    }

def create_wallet_for_user(user_id):
    """Generate wallet and save it to DB if user has no wallet."""
    if get_wallet(user_id):
        return get_wallet_by_user(user_id)

    wallet = generate_tron_wallet()
    create_user(user_id, wallet['address'], wallet['private_key'])
    return {
        "address": wallet['address'],
        "private_key": wallet['private_key'],
        "trx_balance": 0,
        "usdt_balance": 0
    }

def get_wallet_by_user(user_id):
    from db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.wallet_address, u.private_key, b.trx_balance, b.usdt_balance
        FROM users u
        LEFT JOIN balances b ON u.telegram_id = b.telegram_id
        WHERE u.telegram_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        return {
            "address": row["wallet_address"],
            "private_key": row["private_key"],
            "trx_balance": float(row["trx_balance"] or 0),
            "usdt_balance": float(row["usdt_balance"] or 0)
        }
    return None

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

# Optional test
if __name__ == "__main__":
    new_wallet = generate_tron_wallet()
    print(f"🔐 Address: {new_wallet['address']}")
    print(f"🔑 Private Key: {new_wallet['private_key']}")
    trx, usdt = get_wallet_balances(new_wallet['address'])
    print(f"💰 TRX: {trx:.6f} | 💵 USDT: {usdt:.6f}")
