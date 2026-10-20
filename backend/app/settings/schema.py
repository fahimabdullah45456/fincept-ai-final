"""Additive v11 account preferences. Canonical financial records are unchanged."""
def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        preferences_json TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL
    )''')
    if conn.execute('PRAGMA user_version').fetchone()[0] < 11:
        conn.execute('PRAGMA user_version=11')
