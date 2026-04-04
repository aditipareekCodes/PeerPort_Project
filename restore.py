import sqlite3

conn = sqlite3.connect('peerport.db')
# This forces all hidden/pending items back onto the marketplace
conn.execute("UPDATE listings SET status = 'Available'")
conn.commit()
conn.close()

print("✅ All items restored to the Marketplace!")