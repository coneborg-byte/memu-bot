import sqlite3
import os

DB_PATH = "library/knowledge/kb.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT,
            source_url TEXT,
            title TEXT,
            raw_text TEXT,
            summary TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_entry(source_type, source_url, title, raw_text, summary=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO entries (source_type, source_url, title, raw_text, summary)
        VALUES (?, ?, ?, ?, ?)
    ''', (source_type, source_url, title, raw_text, summary))
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id

def get_entry(entry_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entries WHERE id = ?', (entry_id,))
    row = cursor.fetchone()
    conn.close()
    return row

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
