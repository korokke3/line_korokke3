import sqlite3

conn = sqlite3.connect("dictionary.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    content TEXT NOT NULL,
    user_id TEXT NOT NULL,
    private INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS delete_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    voter_id TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ SQLiteデータベース初期化完了！")
