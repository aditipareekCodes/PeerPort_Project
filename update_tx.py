import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            buyer_id TEXT,
            seller_id TEXT,
            status TEXT DEFAULT 'Active'
        )
    ''')
    print("✅ Transactions table successfully created! The loop is ready.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Database Error: {e}")
    
conn.commit()
conn.close()