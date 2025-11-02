import sqlite3, os
from app.errors import DatabaseError

DB_PATH = "data/users.db"

def _ensure_schema(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        wpm REAL,
        accuracy REAL,
        duration REAL,
        weak_keys_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    _ensure_schema(conn)
    return conn

def upsert_user(username: str) -> int:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users(username) VALUES (?)", (username,))
        conn.commit()
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        return row[0]
    except Exception as e:
        raise DatabaseError(str(e))
    finally:
        conn.close()

def insert_result(user_id: int, wpm: float, accuracy: float, duration: float, weak_keys_json: str):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO results(user_id, wpm, accuracy, duration, weak_keys_json) VALUES (?,?,?,?,?)",
            (user_id, wpm, accuracy, duration, weak_keys_json)
        )
        conn.commit()
    except Exception as e:
        raise DatabaseError(str(e))
    finally:
        conn.close()
