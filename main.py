

import time
from logger import logger
import threading
from flask import Flask
from db import create_tables, USE_LOCAL_DB, DB_FILE_PATH
from profit_bridge_bot import bot, init_bot



# --- Dummy Flask Server to Keep Render Web Service Active ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!", 200

def run_flask():
    logger.info("🌐 Dummy Flask server running...")
    app.run(host="0.0.0.0", port=10000)

# --- Main Bot Runner ---
def run_bot():
    try:
        create_tables()
        if USE_LOCAL_DB:
            logger.info(f"✅ Local DB file: {DB_FILE_PATH}")
        else:
            logger.info("✅ PostgreSQL tables created (if not already).")
    except Exception as e:
        logger.error(f"❌ Error during DB setup: {e}")

    try:
        logger.info("🚀 Bot is starting polling and Render process is active.")

        init_bot()  # ✅ New line here — moves all setup from profit_bridge_bot into a single call

        while True:
            try:
                bot.polling(none_stop=True, interval=2, timeout=30)
            except Exception as e:
                logger.error(f"❌ Bot crashed: {e}")
                logger.info("🔄 Restarting polling in 15 seconds...")
                time.sleep(15)
                try:
                    bot.delete_webhook()
                    logger.info("✅ Webhook cleared before restart")
                except Exception as e:
                    logger.warning(f"⚠️ Webhook reset failed: {e}")
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down.")


# === MAIN ENTRY POINT ===
if __name__ == "__main__":
    # Start dummy Flask in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Telegram bot
    run_bot()





