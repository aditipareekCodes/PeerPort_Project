import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    conn.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT DEFAULT 'default_avatar.png'")
    print("✅ Users table successfully upgraded with Profile Pictures!")
except sqlite3.OperationalError:
    print("⚠️ Column already exists. You are good to go!")
conn.commit()
conn.close()