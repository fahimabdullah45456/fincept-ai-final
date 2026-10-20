"""Additive v9: keep canonical finance and assistant tables intact."""
def initialize(c):
    c.executescript('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_planner_goal_owner ON financial_goals(id,user_id,dataset);
    CREATE TABLE IF NOT EXISTS planner_occasions (
      goal_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,
      occasion_type TEXT NOT NULL,custom_type TEXT NOT NULL DEFAULT '',start_date TEXT NOT NULL,
      frequency TEXT NOT NULL CHECK(frequency IN ('Weekly','Monthly')),planned_minor INTEGER NOT NULL DEFAULT 0 CHECK(planned_minor>=0),
      UNIQUE(goal_id,user_id,dataset),
      FOREIGN KEY(goal_id,user_id,dataset) REFERENCES financial_goals(id,user_id,dataset)
    );
    CREATE TABLE IF NOT EXISTS planner_tasks (
      id TEXT PRIMARY KEY,user_id TEXT NOT NULL,dataset TEXT NOT NULL,
      title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',due_date TEXT NOT NULL,due_time TEXT,
      timezone TEXT NOT NULL,category TEXT NOT NULL,priority TEXT NOT NULL CHECK(priority IN ('Low','Medium','High')),
      status TEXT NOT NULL CHECK(status IN ('To Do','In Progress','Completed','Cancelled')),
      plan_id TEXT,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      FOREIGN KEY(user_id,dataset) REFERENCES financial_workspaces(user_id,dataset),
      FOREIGN KEY(plan_id,user_id,dataset) REFERENCES planner_occasions(goal_id,user_id,dataset)
    );
    CREATE INDEX IF NOT EXISTS idx_planner_tasks_scope ON planner_tasks(user_id,dataset,due_date,status);
    ''')
    if c.execute('PRAGMA user_version').fetchone()[0]<9:c.execute('PRAGMA user_version=9')
