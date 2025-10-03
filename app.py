import os
import sqlite3
from datetime import datetime
from typing import Any

from flask import Flask, g, redirect, render_template, request, url_for, abort, flash


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["DATABASE"] = os.path.join(app.root_path, "appointments.db")
    

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])  # type: ignore[attr-defined]
            g.db.row_factory = sqlite3.Row  # type: ignore[attr-defined]
        return g.db  # type: ignore[return-value]

    @app.teardown_appcontext
    def close_db(_exc: Exception | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db() -> None:
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                reason TEXT NOT NULL
            );
            """
        )
        db.commit()

    @app.before_request
    def ensure_db_initialized() -> None:
        if not os.path.exists(app.config["DATABASE"]):
            os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
            init_db()
        

    # Routes using .html paths to match static links exactly
    @app.get("/")
    @app.get("/index.html")
    def index_html():
        return render_template("index.html")

    @app.get("/book.html")
    def book_html():
        # If editing, id can be passed by query string
        appt_id = request.args.get("id", type=int)
        appt = None
        if appt_id:
            db = get_db()
            appt = db.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
            if not appt:
                abort(404)
        return render_template("book.html", appt=appt, errors={})

    def validate_payload(payload: dict[str, str]) -> dict[str, str]:
        errors: dict[str, str] = {}
        name = payload.get("name", "").strip()
        email = payload.get("email", "").strip()
        date_str = payload.get("date", "").strip()
        time_str = payload.get("time", "").strip()
        reason = payload.get("reason", "").strip()

        if not name:
            errors["name"] = "Name is required."
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            errors["email"] = "Enter a valid email address."
        if not date_str:
            errors["date"] = "Date is required."
        else:
            try:
                date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_val < datetime.now().date():
                    errors["date"] = "Date cannot be in the past."
            except ValueError:
                errors["date"] = "Invalid date format."
        if not time_str:
            errors["time"] = "Time is required."
        else:
            try:
                _ = datetime.strptime(time_str, "%H:%M").time()
                if not ("09:00" <= time_str <= "17:00"):
                    errors["time"] = "Time must be between 09:00 and 17:00."
            except ValueError:
                errors["time"] = "Invalid time format."
        if not reason:
            errors["reason"] = "Reason is required."
        return errors

    @app.post("/submit.html")
    def submit_html():
        payload: dict[str, str] = {
            "name": request.form.get("name", ""),
            "email": request.form.get("email", ""),
            "date": request.form.get("date", ""),
            "time": request.form.get("time", ""),
            "reason": request.form.get("reason", ""),
        }
        errors = validate_payload(payload)
        if errors:
            return render_template("book.html", appt=payload, errors=errors), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO appointments (name, email, date, time, reason) VALUES (?, ?, ?, ?, ?)",
            (payload["name"].strip(), payload["email"].strip(), payload["date"].strip(), payload["time"].strip(), payload["reason"].strip()),
        )
        db.commit()
        new_id = cur.lastrowid
        return redirect(url_for("success_html", id=new_id))

    @app.get("/success.html")
    def success_html():
        appt_id = request.args.get("id", type=int)
        if not appt_id:
            return redirect(url_for("index_html"))
        db = get_db()
        appt = db.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
        if not appt:
            abort(404)
        return render_template("success.html", appt=appt)

    @app.get("/appointments.html")
    def appointments_html():
        db = get_db()
        appts = db.execute("SELECT * FROM appointments ORDER BY date ASC, time ASC").fetchall()
        message = request.args.get("msg")
        return render_template("appointments.html", appointments=appts, message=message)

    @app.get("/edit.html")
    def edit_html():
        appt_id = request.args.get("id", type=int)
        if not appt_id:
            return redirect(url_for("appointments_html"))
        db = get_db()
        appt = db.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
        if not appt:
            abort(404)
        # Reuse book form with prefilled data
        return render_template("book.html", appt=appt, errors={})

    @app.post("/update.html")
    def update_html():
        appt_id = request.form.get("id", type=int)
        if not appt_id:
            return redirect(url_for("appointments_html"))
        payload: dict[str, str] = {
            "name": request.form.get("name", ""),
            "email": request.form.get("email", ""),
            "date": request.form.get("date", ""),
            "time": request.form.get("time", ""),
            "reason": request.form.get("reason", ""),
        }
        errors = validate_payload(payload)
        if errors:
            appt: dict[str, Any] = dict(payload)
            appt["id"] = appt_id
            return render_template("book.html", appt=appt, errors=errors), 400
        db = get_db()
        db.execute(
            "UPDATE appointments SET name = ?, email = ?, date = ?, time = ?, reason = ? WHERE id = ?",
            (payload["name"].strip(), payload["email"].strip(), payload["date"].strip(), payload["time"].strip(), payload["reason"].strip(), appt_id),
        )
        db.commit()
        return redirect(url_for("appointments_html", msg="Appointment updated"))

    @app.post("/delete.html")
    def delete_html():
        appt_id = request.form.get("id", type=int)
        if appt_id is None:
            return redirect(url_for("appointments_html"))
        db = get_db()
        existing = db.execute("SELECT id FROM appointments WHERE id = ?", (appt_id,)).fetchone()
        if not existing:
            return redirect(url_for("appointments_html", msg="Not found"))
        db.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
        db.commit()
        return redirect(url_for("appointments_html", msg="Appointment deleted"))

    

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


