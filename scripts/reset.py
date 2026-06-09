import sqlite3

conn = sqlite3.connect('peerport.db')
# Force every single item in the database back to "Available"
conn.execute('UPDATE listings SET status = "Available"')
conn.commit()
conn.close()

print("✅ SUCCESS: All ghost items have been reset to 'Available'!")