import sqlite3

DB_PATH = "waste.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

        # tabel reward_redemptions
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reward_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            wallet_type TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            points INTEGER NOT NULL,       -- jumlah poin yang diredeem
            amount INTEGER NOT NULL,       -- jumlah rupiah (saat ini = points)
            status TEXT NOT NULL DEFAULT 'PENDING',
            requested_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        """
    )


    conn.commit()
    conn.close()
