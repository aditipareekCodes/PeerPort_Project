import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    # 1. Nuke the old, broken table from orbit
    conn.execute("DROP TABLE IF EXISTS transactions")
    
    # 2. Build the brand new, correct one
    conn.execute('''
        CREATE TABLE transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            buyer_id TEXT,
            seller_id TEXT,
            status TEXT DEFAULT 'Active'
        )
    ''')
    print("✅ Old table destroyed. New Transactions table perfectly created!")
except sqlite3.OperationalError as e:
    print(f"⚠️ Database Error: {e}")
    
conn.commit()
conn.close()