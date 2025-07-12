# test_all_modules.py

# ✅ Importing only necessary functions and classes (no wallet creation)
from wallet_manager import get_wallet_by_user
from balance import refresh_user_balance
from sweep import sweep_usdt_to_master
from db import get_connection, update_balance, log_transaction
from deposit_checker import check_and_log_deposits
from handle_mint import handle_mint
from config import TRONGRID_API_KEY, USDT_CONTRACT_ADDRESS, MASTER_WALLET_ADDRESS
import logging

if __name__ == "__main__":
    print("🔍 Running module import test...\n")

    try:
        # Test wallet_manager functions (without creating any wallet)
        print("✅ wallet_manager loaded (get_wallet_by_user)")

        # Test balance manager
        print("✅ refresh_user_balance from balance.py is ready")

        # Test sweep function
        print("✅ sweep_usdt_to_master imported from sweep.py")

        # Test database utilities
        conn = get_connection()
        print("✅ db connection and functions (get_connection, update_balance, log_transaction) loaded")

        # Test deposit checker logic
        print("✅ deposit_checker.check_and_log_deposits() is ready")

        # Test mint command handler
        print("✅ handle_mint (Telegram command handler) is available")

        # Config verification
        print(f"✅ config values loaded:\n"
              f"   - TRONGRID_API_KEY: {TRONGRID_API_KEY[:5]}***\n"
              f"   - MASTER_WALLET_ADDRESS: {MASTER_WALLET_ADDRESS}\n"
              f"   - USDT_CONTRACT_ADDRESS: {USDT_CONTRACT_ADDRESS}")

        print("\n🎉 All critical modules and imports passed successfully.")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
