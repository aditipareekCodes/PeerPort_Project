import sqlite3

# Connect to your database
conn = sqlite3.connect('peerport.db')
cursor = conn.cursor()

print("🔧 Attempting to repair database schema...")

# 1. Drop the old transactions table (clears the mismatch)
cursor.execute('DROP TABLE IF EXISTS transactions')

# 2. Re-create it with the EXACT column name 'transaction_id' that app.py expects
cursor.execute('''
    CREATE TABLE transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        buyer_id TEXT,
        seller_id TEXT,
        deal_status TEXT,
        FOREIGN KEY(item_id) REFERENCES listings(item_id),
        FOREIGN KEY(buyer_id) REFERENCES users(moodle_id),
        FOREIGN KEY(seller_id) REFERENCES users(moodle_id)
    )
''')

conn.commit()
conn.close()
print("✅ SUCCESS: Database repaired! The 'transactions' table now uses 'transaction_id'.")