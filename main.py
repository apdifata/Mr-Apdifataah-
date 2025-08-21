import os
import psycopg2
import uuid
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Environment variables from Railway
TOKEN = os.environ.get('TOKEN')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_PORT = os.environ.get('DB_PORT')

# Set amount per referral
REFERRAL_AMOUNT = 2.5

# Connect to PostgreSQL database
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def start(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    chat_id = update.effective_chat.id
    
    # Check if user already exists
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, referral_link FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()

    referral_code = str(uuid.uuid4())
    referral_link = f"https://t.me/your_bot_username?start={referral_code}" # Replace 'your_bot_username' with your bot's username

    if user is None:
        # New user
        referred_by_id = None
        # Check if they were referred
        if context.args:
            referred_by_code = context.args[0]
            cur.execute("SELECT user_id FROM users WHERE referral_code = %s", (referred_by_code,))
            referrer = cur.fetchone()
            if referrer:
                referred_by_id = referrer[0]
                # Add money to referrer's balance
                cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (REFERRAL_AMOUNT, referred_by_id))
        
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, referral_code, referral_link, referred_by_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, username, first_name, referral_code, referral_link, referred_by_id)
        )
        conn.commit()
        
        update.message.reply_text(f"Hello, {first_name}! Your unique referral link is:\n{referral_link}")
        if referred_by_id:
            update.message.reply_text(f"You've been referred! The person who referred you has earned ${REFERRAL_AMOUNT}.")
    else:
        # Existing user
        existing_link = user[1]
        update.message.reply_text(f"Welcome back, {first_name}! Your unique referral link is still active:\n{existing_link}")

    cur.close()
    conn.close()

def balance(update, context):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        balance = user[0]
        update.message.reply_text(f"Your current balance is: ${balance}")
    else:
        update.message.reply_text("Please use the /start command first to register.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
