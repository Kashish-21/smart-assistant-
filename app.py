from flask import Flask, render_template, request, redirect, flash, session, jsonify
from datetime import date
import os
import requests
from dotenv import load_dotenv

from database import (
    init_db,

    # USERS
    get_user_by_username, create_user,

    # TODO
    add_task, get_tasks, delete_task, toggle_task,
    clear_completed, get_categories,

    # CALENDAR
    add_event, get_events_for_user, get_events_for_date,
    get_event, update_event, delete_event, get_upcoming_events,

    # EXPENSES
    add_transaction, get_transactions, delete_transaction,
    get_exp_categories, get_budget,
    get_totals_by_month, get_category_totals,
    get_monthly_summary, get_recent_transactions,

    # HELPERS
    get_current_month
)

# -------------------- UTILS --------------------
def get_previous_month(month):
    year, m = map(int, month.split("-"))
    return f"{year-1}-12" if m == 1 else f"{year}-{m-1:02d}"

# -------------------- APP SETUP --------------------
load_dotenv()
app = Flask(__name__)
app.secret_key = "smart-assistant-secret-key"
init_db()

OWM_API_KEY = os.getenv("OWM_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

DEFAULT_CATEGORIES = ["General", "Work", "Personal", "Shopping", "Study"]
PRIORITY_LEVELS = ["High", "Medium", "Low"]

# -------------------- AUTH --------------------
@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_user_by_username(request.form["username"].strip())
        if not user or user["pin"] != request.form["pin"].strip():
            flash("Invalid credentials", "danger")
            return redirect("/login")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/dashboard")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if get_user_by_username(request.form["username"]):
            flash("Username already exists", "warning")
            return redirect("/signup")

        create_user(request.form["username"], request.form["pin"])
        flash("Account created successfully!", "success")
        return redirect("/login")

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# -------------------- TODO --------------------
@app.route("/todo", methods=["GET", "POST"])
def todo_page():
    if request.method == "POST":
        add_task(
            request.form["new_task"],
            request.form["category"],
            request.form["priority"],
            request.form.get("due_date") or None
        )
        return redirect("/todo")

    tasks = get_tasks("", "All", "All", "due_date")
    categories = list(dict.fromkeys(DEFAULT_CATEGORIES + get_categories()))

    return render_template(
        "todo.html",
        tasks=tasks,
        categories=categories,
        priorities=PRIORITY_LEVELS
    )

@app.route("/toggle/<int:id>/<int:status>")
def toggle(id, status):
    toggle_task(id, status)
    return redirect("/todo")

@app.route("/delete/<int:id>")
def delete(id):
    delete_task(id)
    return redirect("/todo")

@app.route("/clear_completed")
def clear_done():
    clear_completed()
    return redirect("/todo")

# -------------------- CALENDAR --------------------
@app.route("/calendar")
def calendar_page():
    uid = session.get("user_id")
    if not uid:
        return redirect("/login")

    today = date.today().isoformat()
    return render_template(
        "calendar.html",
        today=today,
        events_all=get_events_for_user(uid),
        events_today=get_events_for_date(uid, today),
        upcoming=get_upcoming_events(uid)
    )

@app.route("/calendar/add", methods=["POST"])
def calendar_add():
    add_event(
        session["user_id"],
        request.form["title"],
        request.form["date"],
        request.form.get("time"),
        request.form.get("category"),
        1 if request.form.get("important") else 0,
        request.form.get("reminder_at"),
        request.form.get("notes")
    )
    return redirect("/calendar")

@app.route("/calendar/delete/<int:id>")
def calendar_delete(id):
    delete_event(id)
    return redirect("/calendar")

# -------------------- POMODORO --------------------
@app.route("/pomodoro")
def pomodoro():
    return render_template("pomodoro.html")

# -------------------- EXPENSE DASHBOARD --------------------
@app.route("/expenses")
def expenses_page():
    uid = session.get("user_id")
    if not uid:
        return redirect("/login")

    month = get_current_month()
    prev_month = get_previous_month(month)

    totals = get_totals_by_month(month)
    prev_totals = get_totals_by_month(prev_month)

    cats, cat_values = get_category_totals(month)
    dates, incomes, expenses = get_monthly_summary(month)
    recent = get_recent_transactions()
    budget = get_budget(month)

    spent = totals["expense"]
    budget_used_pct = int((spent / budget) * 100) if budget else 0
    expense_diff = totals["expense"] - prev_totals["expense"]

    return render_template(
        "expenses_dashboard.html",
        month=month,
        totals=totals,
        categories_names=cats,
        category_totals=cat_values,
        dates=dates,
        incomes=incomes,
        expenses=expenses,
        recent=recent,
        budget_amount=budget,
        budget_used_pct=budget_used_pct,
        expense_diff=expense_diff
    )

# -------------------- TRANSACTIONS --------------------
@app.route("/transactions", methods=["GET", "POST"])
def transactions_page():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        add_transaction(
            float(request.form["amount"]),
            request.form.get("category_id") or None,
            request.form["type"],
            request.form["date"],
            request.form.get("payment_method"),
            request.form.get("description")
        )
        return redirect("/transactions")

    return render_template(
        "transactions.html",
        transactions=get_transactions(),
        categories=get_exp_categories()
    )

@app.route("/transactions/delete/<int:id>")
def transactions_delete(id):
    delete_transaction(id)
    return redirect("/transactions")

# -------------------- SMART INSIGHTS --------------------
@app.route("/insights")
def insights_page():
    if "user_id" not in session:
        return redirect("/login")

    tasks = get_tasks("", "All", "All", "due_date")

    total_tasks = len(tasks)

    completed_tasks = 0
    for t in tasks:
        # SAFELY check available keys
        if "status" in t.keys() and t["status"] == 1:
            completed_tasks += 1
        elif "completed" in t.keys() and t["completed"] == 1:
            completed_tasks += 1

    pending_tasks = total_tasks - completed_tasks

    completion_rate = int((completed_tasks / total_tasks) * 100) if total_tasks else 0

    # Expense comparison (ALWAYS defined)
    month = get_current_month()
    prev_month = get_previous_month(month)

    totals = get_totals_by_month(month)
    prev_totals = get_totals_by_month(prev_month)

    expense_diff = totals["expense"] - prev_totals["expense"]

    return render_template(
        "insights.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        completion_rate=completion_rate,
        expense_diff=expense_diff,
        month=month,
        prev_month=prev_month
    )

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(debug=True)
