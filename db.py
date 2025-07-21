

#db.py 


import os
import json
from datetime import datetime

# === CONFIG ===
USE_LOCAL_DB = False  # Set to False to enable PostgreSQL
LOCAL_DB_PATH = "local_db.json"

# PostgreSQL DB CONFIG
DB_HOST = "dpg-d1on093e5dus73edg480-a.oregon-postgres.render.com"
DB_NAME = "profit_bridge_db"
DB_USER = "profit_bridge_db_user"
DB_PASSWORD = "AKU84McNSyOJMDumdqxiIy0PuWYEqPBe"
DB_PORT = 5432

# --- Ensure DB File Exists ---
if USE_LOCAL_DB and not os.path.exists(LOCAL_DB_PATH):
    with open(LOCAL_DB_PATH, "w") as f:
        json.dump({"users": [], "balances": [], "transactions": []}, f, indent=2)

def read_db():
    with open(LOCAL_DB_PATH, "r") as f:
        return json.load(f)

def write_db(data):
    with open(LOCAL_DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

# --- Dummy Connection Object ---
class DummyCursor:
    def execute(self, *args, **kwargs): pass
    def close(self): pass
    def fetchone(self): return None
    def fetchall(self): return []

class DummyConnection:
    def cursor(self): return DummyCursor()
    def commit(self): pass
    def close(self): pass

def get_connection():
    if USE_LOCAL_DB:
        return DummyConnection()
    else:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            cursor_factory=RealDictCursor
        )

# --- Table Creator ---
def create_tables():
    if USE_LOCAL_DB:
        return  # JSON doesn't need table creation

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                wallet_address TEXT,
                private_key TEXT,
                full_name TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE REFERENCES users(telegram_id),
                trx_balance NUMERIC DEFAULT 0,
                usdt_balance NUMERIC DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT REFERENCES users(telegram_id),
                tx_type TEXT,
                token TEXT,
                amount NUMERIC,
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)


        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ create_tables() failed: {e}")

# === Testing Utilities ===
def save_data(telegram_id, wallet_data):
    telegram_id = int(telegram_id)
    db = read_db()
    db["users"] = [u for u in db["users"] if int(u.get("telegram_id", -1)) != telegram_id]
    db["users"].append({
        "telegram_id": telegram_id,
        "wallet_address": wallet_data["address"],
        "private_key": wallet_data["private_key"]
    })
    write_db(db)

def load_data(telegram_id):
    telegram_id = int(telegram_id)
    db = read_db()
    return next((u for u in db["users"] if int(u.get("telegram_id", -1)) == telegram_id), None)

def get_full_wallet(telegram_id):
    telegram_id = int(telegram_id)
    if USE_LOCAL_DB:
        db_data = read_db()
        return next((u for u in db_data["users"] if int(u.get("telegram_id", -1)) == telegram_id), None)
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT wallet_address, private_key FROM users WHERE telegram_id = %s", (telegram_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result

def create_user(telegram_id, wallet_address, private_key, full_name=None):
    telegram_id = int(telegram_id)
    if USE_LOCAL_DB:
        db = read_db()
        if not any(int(u.get("telegram_id", -1)) == telegram_id for u in db["users"]):
            db["users"].append({
                "telegram_id": telegram_id,
                "wallet_address": wallet_address,
                "private_key": private_key,
                "full_name": full_name
            })
            write_db(db)
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (telegram_id, wallet_address, private_key, full_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO NOTHING;
        """, (telegram_id, wallet_address, private_key, full_name))
        conn.commit()
        cur.close()
        conn.close()

def update_user_info(telegram_id, full_name=None):
    telegram_id = int(telegram_id)
    if USE_LOCAL_DB:
        db = read_db()
        for user in db["users"]:
            if int(user.get("telegram_id", -1)) == telegram_id:
                if full_name is not None:
                    user["full_name"] = full_name
                write_db(db)
                return True
        return False
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET full_name = %s WHERE telegram_id = %s
        """, (full_name, telegram_id))
        conn.commit()
        cur.close()
        conn.close()

def get_or_create_wallet(telegram_id):
    telegram_id = int(telegram_id)

    # 1. Check if wallet exists
    existing = get_full_wallet(telegram_id)
    if existing:
        return {
            "address": existing["wallet_address"],
            "private_key": existing["private_key"]
        }

    # 2. Wallet not found — generate and save new one
    try:
        from wallet_manager import generate_tron_wallet  # Lazy import to avoid circular dependency
        wallet = generate_tron_wallet()

        # Save to DB
        create_user(telegram_id, wallet['address'], wallet['private_key'])

        return wallet
    except Exception as e:
        print(f"❌ get_or_create_wallet failed for {telegram_id}: {e}")
        return None


def get_wallet(telegram_id):
    telegram_id = int(telegram_id)
    if USE_LOCAL_DB:
        db = read_db()
        user = next((u for u in db["users"] if int(u.get("telegram_id", -1)) == telegram_id), None)
        return user["wallet_address"] if user else None
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT wallet_address FROM users WHERE telegram_id = %s", (telegram_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result["wallet_address"] if result else None

def update_balance(telegram_id, trx, usdt):
    telegram_id = int(telegram_id)
    if USE_LOCAL_DB:
        db = read_db()
        existing = next((b for b in db["balances"] if int(b.get("telegram_id", -1)) == telegram_id), None)
        if existing:
            existing["trx_balance"] = trx
            existing["usdt_balance"] = usdt
            existing["updated_at"] = datetime.now().isoformat()
        else:
            db["balances"].append({
                "telegram_id": telegram_id,
                "trx_balance": trx,
                "usdt_balance": usdt,
                "updated_at": datetime.now().isoformat()
            })
        write_db(db)
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO balances (telegram_id, trx_balance, usdt_balance)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
            trx_balance = EXCLUDED.trx_balance,
            usdt_balance = EXCLUDED.usdt_balance,
            updated_at = NOW();
        """, (telegram_id, trx, usdt))
        conn.commit()
        cur.close()
        conn.close()

def log_transaction(telegram_id, tx_type, token, amount, tx_hash=None):
    telegram_id = int(telegram_id)
    if USE_LOCAL_DB:
        db = read_db()
        db["transactions"].append({
            "telegram_id": telegram_id,
            "tx_type": tx_type,
            "token": token,
            "amount": amount,
            "tx_hash": tx_hash,
            "created_at": datetime.now().isoformat()
        })
        write_db(db)
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transactions (telegram_id, tx_type, token, amount, tx_hash)
            VALUES (%s, %s, %s, %s, %s);
        """, (telegram_id, tx_type, token, amount, tx_hash))
        conn.commit()
        cur.close()
        conn.close()

# Expose the local DB file path for debugging
DB_FILE_PATH = LOCAL_DB_PATH

# --- Init ---
if __name__ == "__main__":
    create_tables()
    if USE_LOCAL_DB:
        print(f"✅ Local DB file: {DB_FILE_PATH}")
    else:
        print("✅ PostgreSQL tables created (if not already).")



