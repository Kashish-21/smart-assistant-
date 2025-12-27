# database.py (FINAL FULL WORKING VERSION)
import sqlite3
from typing import List, Optional, Any
from datetime import datetime

from datetime import datetime, timedelta
import calendar

DB = "assistant.db"

# ---------------- CONNECTION ----------------
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- INITIALIZE DB ----------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        pin TEXT
    )
    """)

    # Tasks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        category TEXT DEFAULT 'General',
        priority TEXT DEFAULT 'Medium',
        due_date TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Events
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT,
        category TEXT DEFAULT 'Personal',
        important INTEGER DEFAULT 0,
        reminder_at TEXT DEFAULT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # History
    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        command TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Expense Categories
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exp_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

        # --- Add to init_db() (or ensure these CREATEs exist) ---
    # Recurring transactions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recurring_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category_id INTEGER,
        type TEXT NOT NULL,         -- 'income' or 'expense'
        start_date TEXT NOT NULL,   -- YYYY-MM-DD
        frequency TEXT NOT NULL,    -- 'daily','weekly','monthly','yearly'
        every INTEGER DEFAULT 1,    -- every N units (e.g. every 2 months)
        next_date TEXT,             -- next scheduled date (YYYY-MM-DD)
        payment_method TEXT,
        description TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Savings goals table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()


    # Transactions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category_id INTEGER,
        type TEXT NOT NULL,
        date TEXT NOT NULL,
        payment_method TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(category_id) REFERENCES exp_categories(id)
    )
    """)

    # Budgets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT UNIQUE NOT NULL,
        amount REAL NOT NULL
    )
    """)

    # Default categories
    default_categories = ["Food", "Travel", "Bills", "Shopping", "Rent", "Salary", "Entertainment", "Other"]
    for cat in default_categories:
        cur.execute("INSERT OR IGNORE INTO exp_categories (name) VALUES (?)", (cat,))

    conn.commit()
    conn.close()

# ---------------- USER AUTH FUNCTIONS ----------------

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row


def create_user(username, pin):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, pin) VALUES (?, ?)",
        (username, pin)
    )
    conn.commit()
    conn.close()

# ---------------- TASKS ----------------
def add_task(task, category, priority, due_date):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO tasks (task, category, priority, due_date) VALUES (?, ?, ?, ?)",
                (task, category, priority, due_date))
    conn.commit(); conn.close()


def get_tasks(search="", category="", priority="", sort_by="due_date"):
    conn = get_conn(); cur = conn.cursor()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if search:
        query += " AND task LIKE ?"
        params.append(f"%{search}%")

    if category and category != "All":
        query += " AND category=?"
        params.append(category)

    if priority and priority != "All":
        query += " AND priority=?"
        params.append(priority)

    if sort_by == "priority":
        query += " ORDER BY (priority='High') DESC, (priority='Medium') DESC"
    else:
        query += " ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date"

    cur.execute(query, params)
    rows = cur.fetchall(); conn.close()
    return rows


def get_task(task_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
    r = cur.fetchone(); conn.close()
    return r


def update_task(task_id, text, category, priority, due_date):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE tasks SET task=?, category=?, priority=?, due_date=? WHERE id=?",
                (text, category, priority, due_date, task_id))
    conn.commit(); conn.close()


def delete_task(task_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit(); conn.close()


def toggle_task(task_id, status):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE tasks SET completed=? WHERE id=?", (1 - status, task_id))
    conn.commit(); conn.close()


def clear_completed():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE completed=1")
    conn.commit(); conn.close()


def get_categories():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM tasks")
    rows = cur.fetchall()
    conn.close()
    return ["All"] + [r["category"] for r in rows]


# ---------------- EVENTS ----------------
def add_event(user_id, title, date, time, category, important, reminder_at, notes):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO events (user_id, title, date, time, category, important, reminder_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, title, date, time, category, important, reminder_at, notes))
    conn.commit(); conn.close()


def get_events_for_user(user_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE user_id=? ORDER BY date, time", (user_id,))
    rows = cur.fetchall(); conn.close()
    return rows


def get_events_for_date(user_id, d):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE user_id=? AND date=? ORDER BY time", (user_id, d))
    rows = cur.fetchall(); conn.close()
    return rows


def get_event(event_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE id=?", (event_id,))
    r = cur.fetchone(); conn.close()
    return r


def update_event(event_id, title, date, time, category, important, reminder_at, notes):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
    UPDATE events SET title=?, date=?, time=?, category=?, important=?, reminder_at=?, notes=?
    WHERE id=?
    """, (title, date, time, category, important, reminder_at, notes, event_id))
    conn.commit(); conn.close()


def delete_event(event_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit(); conn.close()


def get_upcoming_events(user_id, limit=10):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT * FROM events
        WHERE user_id=? AND date >= date('now')
        ORDER BY date, time LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall(); conn.close()
    return rows


# ---------------- HISTORY ----------------
def log_command(user_id, text):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO history (user_id, command) VALUES (?, ?)", (user_id, text))
    conn.commit(); conn.close()


def get_history(user_id, limit=50):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = cur.fetchall(); conn.close()
    return rows


# ---------------- EXPENSE TRACKER ----------------
def get_current_month():
    return datetime.now().strftime("%Y-%m")


# ----- Categories -----
def get_exp_categories():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM exp_categories ORDER BY name")
    rows = cur.fetchall(); conn.close()
    return rows


def add_exp_category(name):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO exp_categories (name) VALUES (?)", (name,))
    conn.commit(); conn.close()


def update_exp_category(cat_id, new_name):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE exp_categories SET name=? WHERE id=?", (new_name, cat_id))
    conn.commit(); conn.close()


def delete_exp_category(cat_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM exp_categories WHERE id=?", (cat_id,))
    conn.commit(); conn.close()


# ----- Transactions -----
def add_transaction(amount, category_id, type_, date_str, payment_method, description):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions (amount, category_id, type, date, payment_method, description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (amount, category_id, type_, date_str, payment_method, description))
    conn.commit(); conn.close()


def get_transaction(tx_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.amount, t.type, t.date,
               t.payment_method, t.description,
               t.category_id,
               c.name AS category
        FROM transactions t
        LEFT JOIN exp_categories c ON t.category_id = c.id
        WHERE t.id = ?
    """, (tx_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_transaction(tx_id, amount, category_id, type_, date_str, payment_method, description):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE transactions
        SET amount=?, category_id=?, type=?, date=?,
            payment_method=?, description=?
        WHERE id=?
    """, (amount, category_id, type_, date_str, payment_method, description, tx_id))
    conn.commit(); conn.close()


def delete_transaction(tx_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit(); conn.close()


def get_recent_transactions(limit=10):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT t.*, c.name AS category 
        FROM transactions t
        LEFT JOIN exp_categories c ON t.category_id = c.id
        ORDER BY date DESC, id DESC LIMIT ?
    """, (limit,))
    rows = cur.fetchall(); conn.close()
    return rows


def get_totals_by_month(month):
    conn = get_conn(); cur = conn.cursor()

    cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN type='income' THEN amount END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS expense
        FROM transactions
        WHERE strftime('%Y-%m', date)=?
    """, (month,))

    r = cur.fetchone(); conn.close()
    return {
        "income": r["income"],
        "expense": r["expense"],
        "balance": r["income"] - r["expense"]
    }


def get_category_totals(month):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT c.name AS category, 
               COALESCE(SUM(t.amount), 0) AS total
        FROM exp_categories c
        LEFT JOIN transactions t 
            ON t.category_id=c.id 
           AND t.type='expense'
           AND strftime('%Y-%m', t.date)=?
        GROUP BY c.id
        ORDER BY total DESC
    """, (month,))

    rows = cur.fetchall(); conn.close()
    return (
        [r["category"] for r in rows],
        [r["total"] for r in rows]
    )


def get_monthly_summary(month):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT 
            date,
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
        FROM transactions
        WHERE strftime('%Y-%m', date)=?
        GROUP BY date
        ORDER BY date
    """, (month,))
    rows = cur.fetchall(); conn.close()

    return (
        [r["date"] for r in rows],
        [r["income"] for r in rows],
        [r["expense"] for r in rows],
    )


# ----- Budget -----
def set_budget(month, amount):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO budgets (month, amount) VALUES (?, ?)", (month, amount))
    conn.commit(); conn.close()


def get_budget(month):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT amount FROM budgets WHERE month=?", (month,))
    r = cur.fetchone()
    conn.close()
    return r["amount"] if r else None


# Filtering transactions
def get_transactions(limit=500, offset=0, filters=None):
    conn = get_conn(); cur = conn.cursor()

    query = """
        SELECT t.id, t.amount, t.type, t.date,
               t.payment_method, t.description,
               c.name as category
        FROM transactions t
        LEFT JOIN exp_categories c ON t.category_id = c.id
        WHERE 1=1
    """

    params = []

    if filters:
        if filters.get("type"):
            query += " AND t.type=?"
            params.append(filters["type"])

        if filters.get("category_id"):
            query += " AND t.category_id=?"
            params.append(filters["category_id"])

        if filters.get("payment_method"):
            query += " AND t.payment_method=?"
            params.append(filters["payment_method"])

        if filters.get("date_from"):
            query += " AND date(t.date)>=date(?)"
            params.append(filters["date_from"])

        if filters.get("date_to"):
            query += " AND date(t.date)<=date(?)"
            params.append(filters["date_to"])

        if filters.get("search"):
            like = f"%{filters['search']}%"
            query += " AND (t.description LIKE ? OR c.name LIKE ?)"
            params.extend([like, like])

    query += " ORDER BY t.date DESC, t.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- Recurring Transactions Helpers ----------------

def add_recurring_transaction(amount, category_id, type_, start_date, frequency, every=1, payment_method=None, description=None):
    """
    frequency: 'daily', 'weekly', 'monthly', 'yearly'
    every: integer multiplier (e.g., every=2 -> every 2 months)
    """
    conn = get_conn(); cur = conn.cursor()
    # compute next_date initially = start_date
    next_date = start_date
    cur.execute("""
        INSERT INTO recurring_transactions (amount, category_id, type, start_date, frequency, every, next_date, payment_method, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (amount, category_id, type_, start_date, frequency, every, next_date, payment_method, description))
    conn.commit(); conn.close()

def get_active_recurring():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM recurring_transactions WHERE active=1")
    rows = cur.fetchall(); conn.close()
    return rows

def _add_days_to_date(d_str, days=0):
    d = datetime.strptime(d_str, "%Y-%m-%d").date()
    return (d + timedelta(days=days)).isoformat()

def _advance_next_date(cur_date_str, frequency, every):
    d = datetime.strptime(cur_date_str, "%Y-%m-%d").date()
    if frequency == "daily":
        d = d + timedelta(days=every)
    elif frequency == "weekly":
        d = d + timedelta(weeks=every)
    elif frequency == "monthly":
        # add months carefully
        month = d.month - 1 + every
        year = d.year + month // 12
        month = month % 12 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        d = datetime(year, month, day).date()
    elif frequency == "yearly":
        try:
            d = d.replace(year=d.year + every)
        except ValueError:
            # Feb 29 edge
            d = d.replace(month=3, day=1, year=d.year + every)
    return d.isoformat()

def get_recurring_due_dates(today_str=None):
    """
    Return list of recurring rows whose next_date <= today
    """
    if not today_str:
        today_str = datetime.now().date().isoformat()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM recurring_transactions WHERE active=1 AND DATE(next_date) <= DATE(?)", (today_str,))
    rows = cur.fetchall(); conn.close()
    return rows

def update_recurring_next_date(recurring_id, new_next_date):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE recurring_transactions SET next_date=? WHERE id=?", (new_next_date, recurring_id))
    conn.commit(); conn.close()

# Function to actually create a real transaction row for a recurring item
def insert_transaction_from_recurring(rec):
    """
    rec is a Row from recurring_transactions
    """
    # Use existing add_transaction function defined earlier
    category_id = rec["category_id"]
    add_transaction(rec["amount"], category_id, rec["type"], rec["next_date"], rec["payment_method"], rec["description"])

# High-level: process due recurring transactions up to today
def process_recurring_transactions(today_str=None):
    """
    Should be called periodically (on app start and on transactions page load).
    It will insert due transactions and update next_date forward until next_date > today.
    """
    if not today_str:
        today_str = datetime.now().date().isoformat()

    due_list = get_recurring_due_dates(today_str)
    for rec in due_list:
        # keep advancing until next_date > today
        next_date = rec["next_date"]
        while datetime.strptime(next_date, "%Y-%m-%d").date() <= datetime.strptime(today_str, "%Y-%m-%d").date():
            # insert transaction for next_date
            insert_transaction_from_recurring(rec)
            # advance
            next_date = _advance_next_date(next_date, rec["frequency"], rec["every"])
        # update the recurring row with new next_date
        update_recurring_next_date(rec["id"], next_date)

# ---------------- Savings Goals ----------------

def add_savings_goal(name, target_amount, start_date=None, end_date=None):
    if not start_date:
        start_date = datetime.now().date().isoformat()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO savings_goals (name, target_amount, start_date, end_date) VALUES (?, ?, ?, ?)",
                (name, target_amount, start_date, end_date))
    conn.commit(); conn.close()

def get_savings_goals():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM savings_goals ORDER BY created_at DESC")
    rows = cur.fetchall(); conn.close()
    return rows

def get_goal_progress(goal_row):
    """
    Compute progress for a goal:
    - look for transactions whose description contains the goal name (case-insensitive)
    - also include transactions with category name 'Savings' if present
    """
    conn = get_conn(); cur = conn.cursor()
    name = goal_row["name"]
    like = f"%{name}%"
    cur.execute("""
        SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount WHEN type='expense' THEN -amount END),0) as total
        FROM transactions
        WHERE description LIKE ?
    """, (like,))
    row = cur.fetchone()
    conn.close()
    saved = row["total"] if row else 0.0
    # saved could be negative if expense entries - treat positive contributions only
    saved = saved if saved > 0 else 0.0
    progress = (saved / goal_row["target_amount"]) * 100 if goal_row["target_amount"] else 0.0
    return {"saved": round(saved,2), "target": goal_row["target_amount"], "progress_percent": round(progress,2)}


# ---------------- MAIN ----------------
if __name__ == "__main__":
    init_db()
