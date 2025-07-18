import os
import requests

# === Telegram Bot Token ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7159542011:AAFENQhVOFy0V3Slaievmz8rgenxYI5sNDU")

# === Master Wallet & API Configs ===
TATUM_API_KEY = "d39d01f8-556c-4d55-88b1-13490b39b6a6"
TRONGRID_API_KEY = "5538c1ba-2a47-4b78-af41-42411510fa27"

# === Telegram Admin User ID ===
ADMIN_USER_ID = "1355417501"

# === Master Wallet Info ===
MASTER_WALLET_ADDRESS = "TH26JZNzB4DmZFvUEwHHGzfwXnxAzn6Yvu"
MASTER_WALLET_PRIVATE_KEY = "7b25ed1e25eb91347bdcce3ba925e7a30cb8c61e6229d52378926d2e8b13bd38"
USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# === TRC20 ABI for USDT ===
TRC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "success", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
]

# === Tatum: Get TRX Balance ===
def get_tatum_tron_balance(address: str):
    url = f"https://api.tatum.io/v3/tron/account/{address}"
    headers = {"x-api-key": TATUM_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"📡 [Tatum] GET {url} => {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "balance": float(data.get("balance", 0)) / 1_000_000
            }
        else:
            return {
                "success": False,
                "error": f"API responded with {response.status_code}",
                "raw": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# === Tatum: Get USDT Balance (TRC-20) ===
def get_tatum_usdt_balance(address: str):
    url = f"https://api.tatum.io/v3/tron/account/balance/{address}/{USDT_CONTRACT_ADDRESS}"
    headers = {"x-api-key": TATUM_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"📡 [Tatum] GET {url} => {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "balance": float(data.get("balance", 0)) / 1_000_000
            }
        else:
            return {
                "success": False,
                "error": f"API responded with {response.status_code}",
                "raw": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
