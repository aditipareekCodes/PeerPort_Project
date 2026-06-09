import sqlite3

def clear_database():
    conn = sqlite3.connect('peerport.db')
    cursor = conn.cursor()
    
    # List of tables to clear
    tables = ['messages', 'transactions', 'listings', 'users']
    
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Cleared table: {table}")
        except sqlite3.OperationalError:
            print(f"Table {table} does not exist, skipping.")
            
    conn.commit()
    conn.close()
    print("✨ Database is now clean and ready for fresh entries!")

if __name__ == '__main__':
    clear_database()