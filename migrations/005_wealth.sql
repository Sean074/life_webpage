CREATE TABLE IF NOT EXISTS wealth_accounts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    balance      REAL NOT NULL DEFAULT 0,
    type         TEXT NOT NULL DEFAULT 'savings',
    institution  TEXT NOT NULL DEFAULT '',
    last_updated TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS wealth_projection_params (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    annual_salary           REAL    NOT NULL DEFAULT 0,
    annual_spending         REAL    NOT NULL DEFAULT 0,
    salary_growth_rate      REAL    NOT NULL DEFAULT 0.03,
    inflation_rate          REAL    NOT NULL DEFAULT 0.025,
    investment_return_rate  REAL    NOT NULL DEFAULT 0.07,
    retirement_year         INTEGER NOT NULL DEFAULT 2045,
    retirement_spending_adj REAL    NOT NULL DEFAULT 0.8,
    horizon_year            INTEGER NOT NULL DEFAULT 2055
);
