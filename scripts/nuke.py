import sqlite3
conn = sqlite3.connect('peerport.db')
conn.execute("DELETE FROM transactions")
conn.execute("UPDATE listings SET status = 'Available'")
conn.commit()
conn.close()
print("✅ Database cleaned. Ready for fresh test.")