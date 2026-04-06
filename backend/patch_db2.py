import sqlite3
def run():
    try:
        conn = sqlite3.connect('d:/BoneQuest/backend/bonequest.db')
        conn.execute('ALTER TABLE chat_messages ADD COLUMN user_feedback INTEGER DEFAULT 0')
        conn.commit()
        conn.close()
        print('Added user_feedback')
    except Exception as e:
        print(f"Error: {e}")

run()
