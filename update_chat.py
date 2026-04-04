import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    # Creating the table to hold all chat messages
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id INTEGER NOT NULL,
            sender_id TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Messages table successfully created! The chat engine is ready.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Database Error: {e}")
    
conn.commit()
conn.close()