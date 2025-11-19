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
            email TEXT,
            birth_date TEXT,
            region TEXT,
            phone TEXT,
            password_hash TEXT,
            is_phone_verified INTEGER DEFAULT 0
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

    # --- Upgrade DB lama (tambah kolom jika hilang) ---

    # Tambah latitude/longitude jika belum ada
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(bounties)")]
    if "latitude" not in cols:
        conn.execute("ALTER TABLE bounties ADD COLUMN latitude REAL;")
    if "longitude" not in cols:
        conn.execute("ALTER TABLE bounties ADD COLUMN longitude REAL;")

    # Tambah flag is_phone_verified jika belum ada
    cols_users = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
    if "is_phone_verified" not in cols_users:
        conn.execute("ALTER TABLE users ADD COLUMN is_phone_verified INTEGER DEFAULT 0;")

    conn.commit()
    conn.close()
