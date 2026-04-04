import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    conn.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
    conn.execute("ALTER TABLE users ADD COLUMN privacy_mode TEXT DEFAULT 'Email Only'")
    print("✅ Users table successfully upgraded with Phone and Privacy settings!")
except sqlite3.OperationalError:
    print("⚠️ Columns already exist. You are good to go!")
conn.commit()
conn.close()