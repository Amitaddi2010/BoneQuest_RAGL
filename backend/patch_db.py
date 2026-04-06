import sqlite3
def run():
    try:
        conn = sqlite3.connect('d:/BoneQuest/backend/bonequest.db')
        conn.execute('ALTER TABLE documents ADD COLUMN doc_type VARCHAR(50) DEFAULT "general"')
        conn.commit()
        conn.close()
        print('Added doc_type')
    except Exception as e:
        print(f"Error: {e}")

run()
