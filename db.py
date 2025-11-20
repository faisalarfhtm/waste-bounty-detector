import sqlite3

DB_PATH = "waste.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    # # Tambah kolom reason jika belum ada
    # conn.execute("ALTER TABLE reward_redemptions ADD COLUMN reason TEXT DEFAULT NULL")



    conn.commit()
    conn.close()
