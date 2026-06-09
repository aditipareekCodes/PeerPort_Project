import sqlite3

conn = sqlite3.connect('peerport.db')
# This creates the table ONLY if it doesn't already exist!
conn.execute('''
    CREATE TABLE IF NOT EXISTS contact_messages (
        msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        subject TEXT,
        message TEXT NOT NULL,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()

print("✅ SUCCESS: The 'contact_messages' table is ready for incoming tickets!")