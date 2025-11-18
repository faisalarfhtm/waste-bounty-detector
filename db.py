import sqlite3

DB_PATH = "waste.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    # tabel users
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            birth_date TEXT,
            region TEXT,
            phone TEXT,
            password_hash TEXT
        );
        """
    )

    # tabel bounties
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bounties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id TEXT NOT NULL,
            cleaner_id TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            created_at TEXT,
            claimed_at TEXT,
            completed_at TEXT,
            before_image TEXT,
            after_image TEXT,
            status TEXT,
            num_objects INTEGER,
            points_reporter INTEGER,
            points_cleaner INTEGER,
            labels_json TEXT,
            FOREIGN KEY(reporter_id) REFERENCES users(user_id),
            FOREIGN KEY(cleaner_id) REFERENCES users(user_id)
        );
        """
    )

    # jaga-jaga kalau DB lama belum ada kolom lat/lon
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(bounties)")]
    if "latitude" not in cols:
        conn.execute("ALTER TABLE bounties ADD COLUMN latitude REAL;")
    if "longitude" not in cols:
        conn.execute("ALTER TABLE bounties ADD COLUMN longitude REAL;")

    conn.commit()
    conn.close()
