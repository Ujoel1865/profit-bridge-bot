# balance.py

from wallet_manager import get_wallet_by_user, get_wallet_balances, save_wallet

def refresh_user_balance(user_id):
    """
    Refreshes the user's on-chain wallet balance and updates it in storage.

    Args:
        user_id (int): Telegram user ID or unique identifier

    Returns:
        dict: Dictionary containing updated TRX and USDT balances
    """
    wallet = get_wallet_by_user(user_id)
    if not wallet:
        raise ValueError("Wallet not found for user.")

    address = wallet["address"]
    trx, usdt = get_wallet_balances(address)

    # Update wallet dictionary with latest balances
    wallet["trx_balance"] = trx
    wallet["usdt_balance"] = usdt

    # Save updated wallet to local file
    save_wallet(user_id, wallet)

    return {
        "trx_balance": trx,
        "usdt_balance": usdt
    }
