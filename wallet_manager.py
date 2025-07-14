from tronpy import Tron
from tronpy.providers import HTTPProvider
from db import create_user, get_connection

# === CONFIGURATION ===
TRONGRID_API_KEY = "5538c1ba-2a47-4b78-af41-42411510fa27"
USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

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

def get_tron_client():
    return Tron(provider=HTTPProvider(api_key=TRONGRID_API_KEY))

def generate_tron_wallet():
    client = get_tron_client()
    wallet = client.generate_address()
    return {
        "address": wallet['base58check_address'],
        "private_key": wallet['private_key']
    }

# ✅ Save wallet to PostgreSQL
def save_wallet(user_id, wallet):
    address = wallet.get("address")
    private_key = wallet.get("private_key")
    if address and private_key:
        try:
            create_user(user_id, address, private_key)
            print(f"✅ Wallet saved for user {user_id}")
        except Exception as e:
            print(f"❌ Failed to save wallet for user {user_id}: {e}")
    else:
        print(f"❌ Invalid wallet data for user {user_id}")

# ✅ Fetch wallet from PostgreSQL
def get_wallet_by_user(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT wallet_address, private_key FROM users WHERE telegram_id = %s", (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            return {
                "address": result["wallet_address"],
                "private_key": result["private_key"]
            }
    except Exception as e:
        print(f"❌ Error fetching wallet for user {user_id}: {e}")
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

# ✅ Wrapper for generation + saving
def create_wallet_for_user(user_id):
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
