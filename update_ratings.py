import sqlite3

conn = sqlite3.connect('peerport.db')
try:
    # Everyone starts with a perfect 5.0 rating and 1 review to establish trust
    conn.execute("ALTER TABLE users ADD COLUMN seller_rating REAL DEFAULT 5.0")
    conn.execute("ALTER TABLE users ADD COLUMN rating_count INTEGER DEFAULT 1")
    print("✅ Users table successfully upgraded with Seller Ratings!")
except sqlite3.OperationalError:
    print("⚠️ Rating columns already exist. You are good to go!")
conn.commit()
conn.close()