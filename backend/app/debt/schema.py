"""Additive v10: obligations, immutable tracking ledger, shopping and genuine FX cache."""
def initialize(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS debt_records (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('borrowed','lent','emi')),
      name TEXT NOT NULL,counterparty TEXT NOT NULL,principal_minor INTEGER NOT NULL CHECK(principal_minor>0),interest_minor INTEGER NOT NULL CHECK(interest_minor>=0),
      opened_date TEXT NOT NULL,due_date TEXT,first_date TEXT,frequency TEXT NOT NULL,installment_minor INTEGER NOT NULL,installments INTEGER NOT NULL,
      purchase_minor INTEGER NOT NULL,down_minor INTEGER NOT NULL,notes TEXT NOT NULL,archived INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,
      UNIQUE(id,user_id,dataset),FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset)
    );
    CREATE INDEX IF NOT EXISTS debt_scope ON debt_records(user_id,dataset,kind);
    CREATE TABLE IF NOT EXISTS debt_payments (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,debt_id TEXT NOT NULL,principal_minor INTEGER NOT NULL CHECK(principal_minor>=0),
      interest_minor INTEGER NOT NULL CHECK(interest_minor>=0),fee_minor INTEGER NOT NULL CHECK(fee_minor>=0),paid_date TEXT NOT NULL,note TEXT NOT NULL,
      reversal_of TEXT UNIQUE,created_at TEXT NOT NULL,
      FOREIGN KEY(debt_id,user_id,dataset) REFERENCES debt_records(id,user_id,dataset),FOREIGN KEY(reversal_of) REFERENCES debt_payments(id)
    );
    CREATE INDEX IF NOT EXISTS debt_payment_scope ON debt_payments(user_id,dataset,debt_id);
    CREATE TABLE IF NOT EXISTS shopping_lists (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,name TEXT NOT NULL,category TEXT NOT NULL,target_date TEXT,notes TEXT NOT NULL,
      version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,UNIQUE(id,user_id,dataset),
      FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset)
    );
    CREATE TABLE IF NOT EXISTS shopping_items (
      id TEXT PRIMARY KEY,list_id TEXT NOT NULL,user_id TEXT NOT NULL,dataset TEXT NOT NULL,name TEXT NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),
      unit_minor INTEGER NOT NULL CHECK(unit_minor>=0),category TEXT NOT NULL,purchased INTEGER NOT NULL DEFAULT 0,
      actual_minor INTEGER CHECK(actual_minor>=0),purchased_date TEXT,notes TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,
      FOREIGN KEY(list_id,user_id,dataset) REFERENCES shopping_lists(id,user_id,dataset) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS hub_fx_cache (base TEXT PRIMARY KEY,payload TEXT NOT NULL,fetched_at TEXT NOT NULL);
    ''')
    if c.execute('PRAGMA user_version').fetchone()[0]<10:c.execute('PRAGMA user_version=10')
