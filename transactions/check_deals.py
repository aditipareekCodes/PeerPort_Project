import sqlite3
conn = sqlite3.connect('peerport.db')
conn.row_factory = sqlite3.Row
deals = conn.execute("SELECT * FROM transactions").fetchall()
print(f"Total Transactions Found: {len(deals)}")
for d in deals:
    print(f"TX: {d['tx_id']} | Item: {d['item_id']} | Buyer: {d['buyer_id']} | Seller: {d['seller_id']}")
conn.close()