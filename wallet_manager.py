from tronpy import Tron
from tronpy.providers import HTTPProvider
from config import TRONGRID_API_KEY, USDT_CONTRACT_ADDRESS, TRC20_ABI, ADMIN_USER_ID, MASTER_WALLET_ADDRESS, MASTER_WALLET_PRIVATE_KEY
from db import get_connection


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
    """
    Saves or updates a user's wallet in the database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if user already has a wallet
    cursor.execute("SELECT id FROM wallets WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result:
        # Update existing wallet
        cursor.execute("""
            UPDATE wallets 
            SET wallet_address = %s, private_key = %s
            WHERE user_id = %s
        """, (wallet['address'], wallet['private_key'], user_id))
    else:
        # Insert new wallet
        cursor.execute("""
            INSERT INTO wallets (user_id, wallet_address, private_key)
            VALUES (%s, %s, %s)
        """, (user_id, wallet['address'], wallet['private_key']))

    conn.commit()
    cursor.close()
    conn.close()


def get_wallet_by_user(user_id):
    """
    Retrieves the wallet for a specific user from the database.
    Returns the MASTER wallet if user is ADMIN.
    """
    if str(user_id) == str(ADMIN_USER_ID):
        return {
            "address": MASTER_WALLET_ADDRESS,
            "private_key": MASTER_PRIVATE_KEY
        }

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT wallet_address, private_key 
        FROM wallets 
        WHERE user_id = %s
    """, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        return {
            "address": result[0],
            "private_key": result[1]
        }
    return None


def get_wallet_balances(address):
    """
    Returns both TRX and USDT balances for a given wallet address.
    """
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


def create_wallet_for_user(user_id):
    """
    Creates a wallet for a user.
    For admin, returns the MASTER wallet without saving.
    For regular users, generates and saves a new wallet.
    """
    if str(user_id) == str(ADMIN_USER_ID):
        return {
            "address": MASTER_WALLET_ADDRESS,
            "private_key": MASTER_PRIVATE_KEY
        }

    wallet = generate_tron_wallet()
    save_wallet(user_id, wallet)
    return wallet


# Optional test block
if __name__ == "__main__":
    test_wallet = generate_tron_wallet()
    print(f"🔐 Address: {test_wallet['address']}")
    print(f"🔑 Private Key: {test_wallet['private_key']}")
    trx, usdt = get_wallet_balances(test_wallet['address'])
    print(f"💰 TRX: {trx:.6f} | 💵 USDT: {usdt:.6f}")
