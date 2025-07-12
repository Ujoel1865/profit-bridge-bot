# db.py

import psycopg2
from psycopg2.extras import RealDictCursor

# --- DATABASE CONFIG ---
DB_HOST = "dpg-d1on093e5dus73edg480-a.oregon-postgres.render.com"
DB_NAME = "profit_bridge_db"
DB_USER = "profit_bridge_db_user"
DB_PASSWORD = "AKU84McNSyOJMDumdqxiIy0PuWYEqPBe"
DB_PORT = 5432

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )

# --- INITIAL SETUP ---
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        wallet_address TEXT,
        private_key TEXT
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
        tx_type TEXT, -- deposit, withdraw
        token TEXT,   -- USDT or TRX
        amount NUMERIC,
        tx_hash TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

# --- FUNCTIONS ---

def create_user(telegram_id, wallet_address, private_key):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (telegram_id, wallet_address, private_key)
        VALUES (%s, %s, %s)
        ON CONFLICT (telegram_id) DO NOTHING;
    """, (telegram_id, wallet_address, private_key))
    conn.commit()
    cur.close()
    conn.close()

def get_wallet(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT wallet_address FROM users WHERE telegram_id = %s", (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result['wallet_address'] if result else None

def update_balance(telegram_id, trx, usdt):
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions (telegram_id, tx_type, token, amount, tx_hash)
        VALUES (%s, %s, %s, %s, %s);
    """, (telegram_id, tx_type, token, amount, tx_hash))
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        create_tables()
        print("✅ Database connection successful and tables created (if not already).")
    except Exception as e:
        print(f"❌ Error: {e}")