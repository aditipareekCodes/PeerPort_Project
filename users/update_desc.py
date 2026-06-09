import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    conn.execute("ALTER TABLE listings ADD COLUMN description TEXT DEFAULT 'No description provided.'")
    print("✅ Listings table successfully upgraded with Descriptions!")
except sqlite3.OperationalError:
    print("⚠️ Column already exists. You are good to go!")
conn.commit()
conn.close()