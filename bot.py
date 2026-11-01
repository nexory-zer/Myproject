from __future__ import annotations

from datetime import date
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from database import (
    add_goal,
    add_session,
    get_goal,
    get_goal_stats,
    get_goals,
    get_session,
    get_sessions_by_date,
    init_database,
    reset_goal_sessions,
    update_session,
)


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=BASE_DIR / "templates", static_folder=BASE_DIR / "static")
app.config["SECRET_KEY"] = "study-tracker-local-secret"


def current_user_id() -> int:
    """Return the local browser user's id.

    The former Telegram user id is represented by a signed browser session. A
    local installation starts with user 1 and can later be replaced by real
    authentication without changing the database layer.
    """
    if "user_id" not in session:
        session["user_id"] = 1
    return int(session["user_id"])


def format_minutes(minutes: int) -> str:
    hours, remaining = divmod(int(minutes or 0), 60)
    if hours and remaining:
        return f"{hours} ч {remaining} мин"
    if hours:
        return f"{hours} ч"
    return f"{remaining} мин"


def stats_for(goal_id: int) -> dict:
    stats = dict(get_goal_stats(current_user_id(), goal_id))
    stats["total_minutes_label"] = format_minutes(stats["total_minutes"])
    stats["longest_session_label"] = format_minutes(stats["longest_session"])
    stats["max_day_minutes_label"] = format_minutes(stats["max_day_minutes"])
    return stats


@app.context_processor
def inject_helpers():
    return {"format_minutes": format_minutes, "today": date.today().isoformat()}


@app.get("/")
def index():
    goals = get_goals(current_user_id())
    return render_template("dashboard.html", goals=goals)


@app.post("/goals")
def create_goal():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Название цели не может быть пустым.", "error")
    else:
        add_goal(current_user_id(), name)
        flash(f"Цель «{name}» добавлена.", "success")
    return redirect(url_for("index"))


@app.get("/goals/<int:goal_id>")
def goal_detail(goal_id: int):
    goal = get_goal(current_user_id(), goal_id)
    if goal is None:
        flash("Цель не найдена.", "error")
        return redirect(url_for("index"))
    return render_template("goal.html", goal=goal, stats=stats_for(goal_id))


@app.route("/goals/<int:goal_id>/sessions/new", methods=["GET", "POST"])
def new_session(goal_id: int):
    goal = get_goal(current_user_id(), goal_id)
    if goal is None:
        flash("Цель не найдена.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        data, error = read_session_form(request.form)
        if error:
            flash(error, "error")
            return render_template("session_form.html", goal=goal, form=request.form, heading="Новое занятие")
        add_session(current_user_id(), goal_id, data)
        flash("Занятие сохранено.", "success")
        return redirect(url_for("goal_detail", goal_id=goal_id))
    return render_template("session_form.html", goal=goal, form={}, heading="Новое занятие")


def read_session_form(form):
    try:
        duration = int(form.get("duration_minutes", ""))
        total = int(form.get("total_tasks", ""))
        oral = int(form.get("oral_tasks", ""))
        practical = int(form.get("practical_tasks", ""))
    except (TypeError, ValueError):
        return None, "Заполните числовые поля целыми числами."
    if duration <= 0:
        return None, "Длительность должна быть больше нуля."
    if min(total, oral, practical) < 0:
        return None, "Количество заданий не может быть отрицательным."
    if oral + practical != total:
        return None, "Устные и практические задания должны равняться общему количеству."
    selected_date = form.get("date", "").strip() or date.today().isoformat()
    try:
        date.fromisoformat(selected_date)
    except ValueError:
        return None, "Укажите корректную дату."
    comment = form.get("comment", "").strip() or None
    return {
        "date": selected_date,
        "duration_minutes": duration,
        "total_tasks": total,
        "oral_tasks": oral,
        "practical_tasks": practical,
        "comment": comment,
    }, None


@app.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
def edit_session(session_id: int):
    user_id = current_user_id()
    goal_id = request.args.get("goal_id", type=int)
    if goal_id is None:
        flash("Не указана цель занятия.", "error")
        return redirect(url_for("index"))
    goal = get_goal(user_id, goal_id)
    if goal is None:
        flash("Цель не найдена.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        data, error = read_session_form(request.form)
        if error:
            flash(error, "error")
            return render_template("session_form.html", goal=goal, form=request.form, heading="Изменить занятие")
        update_session(session_id, user_id, data)
        flash("Занятие обновлено.", "success")
        return redirect(url_for("goal_detail", goal_id=goal_id))
    existing = get_session(session_id, user_id, goal_id)
    if existing is None:
        flash("Занятие не найдено.", "error")
        return redirect(url_for("goal_detail", goal_id=goal_id))
    return render_template("session_form.html", goal=goal, form=existing, heading="Изменить занятие")


@app.get("/goals/<int:goal_id>/history")
def history(goal_id: int):
    goal = get_goal(current_user_id(), goal_id)
    if goal is None:
        flash("Цель не найдена.", "error")
        return redirect(url_for("index"))
    selected_date = request.args.get("date", date.today().isoformat())
    try:
        date.fromisoformat(selected_date)
    except ValueError:
        selected_date = date.today().isoformat()
        flash("Указана некорректная дата.", "error")
    sessions = get_sessions_by_date(current_user_id(), goal_id, selected_date)
    return render_template("history.html", goal=goal, sessions=sessions, selected_date=selected_date)


@app.post("/goals/<int:goal_id>/reset")
def reset(goal_id: int):
    if get_goal(current_user_id(), goal_id) is None:
        flash("Цель не найдена.", "error")
    else:
        reset_goal_sessions(current_user_id(), goal_id)
        flash("Статистика сброшена.", "success")
    return redirect(url_for("goal_detail", goal_id=goal_id))
init_database()

if __name__ == "__main__":
    app.run(debug=True)

