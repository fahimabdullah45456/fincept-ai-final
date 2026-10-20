"""Additive v8 conversation persistence, independent of canonical accounting rows."""
def initialize(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS assistant_conversations (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      dataset TEXT NOT NULL CHECK(dataset IN ('live','demo')),title TEXT NOT NULL,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(id,user_id,dataset)
    );
    CREATE INDEX IF NOT EXISTS idx_assistant_history ON assistant_conversations(user_id,dataset,updated_at DESC,id);
    CREATE TABLE IF NOT EXISTS assistant_requests (
      id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,user_id TEXT NOT NULL,dataset TEXT NOT NULL,
      content TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','failed','completed')),
      attempt TEXT NOT NULL,error_code TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      FOREIGN KEY(conversation_id,user_id,dataset) REFERENCES assistant_conversations(id,user_id,dataset) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_assistant_requests_conversation ON assistant_requests(conversation_id,created_at,id);
    CREATE TABLE IF NOT EXISTS assistant_messages (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,conversation_id TEXT NOT NULL,
      user_id TEXT NOT NULL,dataset TEXT NOT NULL,request_id TEXT NOT NULL REFERENCES assistant_requests(id) ON DELETE CASCADE,
      role TEXT NOT NULL CHECK(role IN ('user','assistant')),content TEXT NOT NULL,summary_json TEXT,
      provider TEXT,model TEXT,created_at TEXT NOT NULL,UNIQUE(request_id,role),
      FOREIGN KEY(conversation_id,user_id,dataset) REFERENCES assistant_conversations(id,user_id,dataset) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_assistant_messages_conversation ON assistant_messages(conversation_id,seq);
    ''')
    if conn.execute('PRAGMA user_version').fetchone()[0] < 8:
        conn.execute('PRAGMA user_version=8')
