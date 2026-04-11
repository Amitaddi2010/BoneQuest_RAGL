import sqlite3
import os

db_path = "bonequest.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    original_size = os.path.getsize(db_path) / (1024 * 1024)
    print(f"Original size: {original_size:.2f} MB")
    
    print("Running VACUUM...")
    conn = sqlite3.connect(db_path)
    # Set journal mode to DELETE or WAL if needed, but standard VACUUM works directly.
    conn.execute("VACUUM")
    conn.commit()
    conn.close()
    
    new_size = os.path.getsize(db_path) / (1024 * 1024)
    print(f"New size: {new_size:.2f} MB")
    
    print(f"Saved {(original_size - new_size):.2f} MB")
