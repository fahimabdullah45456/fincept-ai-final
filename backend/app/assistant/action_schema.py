"""v12: durable, owner/dataset-bound approvals. No duplicate financial models."""
def initialize(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS assistant_proposals (
      id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,request_id TEXT NOT NULL UNIQUE,
      user_id TEXT NOT NULL,dataset TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,
      status TEXT NOT NULL CHECK(status IN ('pending','cancelled','executed')),
      payload_json TEXT NOT NULL,preview_json TEXT NOT NULL,result_json TEXT,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,expires_at TEXT NOT NULL,
      FOREIGN KEY(conversation_id,user_id,dataset) REFERENCES assistant_conversations(id,user_id,dataset) ON DELETE CASCADE,
      FOREIGN KEY(request_id) REFERENCES assistant_requests(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_assistant_proposals_owner ON assistant_proposals(user_id,dataset,conversation_id);
    ''')
    if conn.execute('PRAGMA user_version').fetchone()[0]<12:conn.execute('PRAGMA user_version=12')
