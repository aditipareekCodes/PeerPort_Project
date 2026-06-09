import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    conn.execute("ALTER TABLE listings ADD COLUMN original_price REAL DEFAULT 0")
    print("✅ Database successfully upgraded with Original Price!")
except sqlite3.OperationalError:
    print("⚠️ Column already exists. You are good to go!")
conn.commit()
conn.close()