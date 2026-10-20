def initialize(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS financial_workspaces (
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      dataset TEXT NOT NULL CHECK(dataset IN ('live','demo')),
      PRIMARY KEY(user_id,dataset)
    );
    CREATE TABLE IF NOT EXISTS wallets (
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL, dataset TEXT NOT NULL,
      name TEXT NOT NULL, opening_minor INTEGER NOT NULL DEFAULT 0,
      opening_date TEXT NOT NULL,
      UNIQUE(id,user_id,dataset),
      FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS transactions (
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL, dataset TEXT NOT NULL,
      wallet_id TEXT NOT NULL, destination_wallet_id TEXT,
      kind TEXT NOT NULL CHECK(kind IN ('income','expense','transfer')),
      amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
      title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', category TEXT,
      occurred_at TEXT NOT NULL, linked_transfer_id TEXT,
      FOREIGN KEY(wallet_id,user_id,dataset) REFERENCES wallets(id,user_id,dataset),
      FOREIGN KEY(destination_wallet_id,user_id,dataset) REFERENCES wallets(id,user_id,dataset),
      FOREIGN KEY(linked_transfer_id,user_id,dataset) REFERENCES transactions(id,user_id,dataset),
      UNIQUE(id,user_id,dataset),
      CHECK((kind='transfer' AND destination_wallet_id IS NOT NULL AND destination_wallet_id<>wallet_id)
         OR (kind<>'transfer' AND destination_wallet_id IS NULL))
    );
    CREATE INDEX IF NOT EXISTS idx_transactions_owner_date ON transactions(user_id,dataset,occurred_at DESC);
    CREATE TABLE IF NOT EXISTS budgets (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,name TEXT NOT NULL,
      category TEXT NOT NULL,limit_minor INTEGER NOT NULL CHECK(limit_minor>=0),
      start_date TEXT NOT NULL,end_date TEXT NOT NULL CHECK(end_date>=start_date),
      FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS financial_goals (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,name TEXT NOT NULL,
      saved_minor INTEGER NOT NULL CHECK(saved_minor>=0), target_minor INTEGER NOT NULL CHECK(target_minor>=0),
      target_date TEXT,
      FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset) ON DELETE CASCADE
    );

    ''')
    # Additive v3 metadata preserves canonical ledger rows and legacy import compatibility.
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS wallet_metadata (
      wallet_id TEXT PRIMARY KEY REFERENCES wallets(id) ON DELETE CASCADE,
      kind TEXT NOT NULL DEFAULT 'bank', currency TEXT NOT NULL DEFAULT 'BDT', archived INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS transaction_metadata (
      transaction_id TEXT PRIMARY KEY REFERENCES transactions(id) ON DELETE CASCADE,
      notes TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1,
      mode TEXT NOT NULL DEFAULT 'transfer', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS custom_categories (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,
      kind TEXT NOT NULL CHECK(kind IN ('income','expense')),name TEXT NOT NULL COLLATE NOCASE,
      UNIQUE(user_id,dataset,kind,name),
      FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS financial_requests (
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, request_key TEXT NOT NULL,
      fingerprint TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(user_id,request_key)
    );

    ''')
    if conn.execute('PRAGMA user_version').fetchone()[0] < 3:
        conn.execute('PRAGMA user_version=3')

    # Presentation-only metadata for custom categories; canonical ledger columns stay unchanged.
    conn.execute("""CREATE TABLE IF NOT EXISTS category_appearance (
      category_id TEXT PRIMARY KEY REFERENCES custom_categories(id) ON DELETE CASCADE,
      icon TEXT NOT NULL DEFAULT 'receipt', color TEXT NOT NULL DEFAULT '#f9733b'
    )""")
    if conn.execute('PRAGMA user_version').fetchone()[0] < 4:
        conn.execute('PRAGMA user_version=4')

    # v5 is additive: canonical IDs, legacy positional inserts and ledger rows survive.
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS wallet_profiles (
      wallet_id TEXT PRIMARY KEY REFERENCES wallets(id) ON DELETE CASCADE,
      provider TEXT NOT NULL DEFAULT '', identifier_last4 TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','inactive')),
      version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS wallet_events (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,wallet_id TEXT NOT NULL,
      delta_minor INTEGER NOT NULL CHECK(delta_minor<>0),
      classification TEXT NOT NULL CHECK(classification IN ('external','adjustment')),
      reason TEXT NOT NULL,source TEXT NOT NULL DEFAULT '',occurred_at TEXT NOT NULL,created_at TEXT NOT NULL,
      FOREIGN KEY(wallet_id,user_id,dataset) REFERENCES wallets(id,user_id,dataset)
    );
    CREATE INDEX IF NOT EXISTS idx_wallet_events_owner ON wallet_events(user_id,dataset,wallet_id,occurred_at);
    """)
    if conn.execute('PRAGMA user_version').fetchone()[0] < 5:
        conn.execute('PRAGMA user_version=5')

    # v6 extends canonical explicit-period budgets without changing ledger or legacy columns.
    conn.execute("""CREATE TABLE IF NOT EXISTS budget_metadata (
      budget_id TEXT PRIMARY KEY REFERENCES budgets(id) ON DELETE CASCADE,
      reset_period TEXT NOT NULL DEFAULT 'custom' CHECK(reset_period IN ('weekly','monthly','custom')),
      alert_threshold INTEGER CHECK(alert_threshold IN (50,75,90,100)),
      notes TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL
    )""")
    if conn.execute('PRAGMA user_version').fetchone()[0] < 6:
        conn.execute('PRAGMA user_version=6')

    # v7: additive goal metadata and immutable contribution audit; canonical columns remain compatible.
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS goal_metadata (
      goal_id TEXT PRIMARY KEY REFERENCES financial_goals(id),
      category TEXT NOT NULL DEFAULT 'Other',description TEXT NOT NULL DEFAULT '',
      monthly_minor INTEGER NOT NULL DEFAULT 0 CHECK(monthly_minor>=0),icon TEXT NOT NULL DEFAULT 'category',
      state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','paused')),
      archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),version INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS goal_contributions (
      id TEXT PRIMARY KEY,goal_id TEXT NOT NULL REFERENCES financial_goals(id),user_id TEXT NOT NULL,dataset TEXT NOT NULL,
      wallet_id TEXT REFERENCES wallets(id),amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
      method TEXT NOT NULL CHECK(method IN ('allocation','external','legacy')),
      wallet_event_id TEXT UNIQUE REFERENCES wallet_events(id),occurred_at TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,
      CHECK((method='legacy' AND wallet_id IS NULL AND wallet_event_id IS NULL) OR
            (method='allocation' AND wallet_id IS NOT NULL AND wallet_event_id IS NULL) OR
            (method='external' AND wallet_id IS NOT NULL AND wallet_event_id IS NOT NULL))
    );
    CREATE INDEX IF NOT EXISTS idx_goal_contributions_owner ON goal_contributions(user_id,dataset,goal_id,occurred_at);
    CREATE INDEX IF NOT EXISTS idx_goal_contributions_wallet ON goal_contributions(wallet_id,occurred_at);
    """)
    if conn.execute('PRAGMA user_version').fetchone()[0] < 7:
        conn.execute('PRAGMA user_version=7')
