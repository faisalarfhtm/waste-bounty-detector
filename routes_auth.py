from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils import get_user
from db import get_db_connection


def init_auth_routes(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            user_id = request.form.get("user_id", "").strip()
            name = request.form.get("name", "").strip()
            birth_date = request.form.get("birth_date", "").strip()
            region = request.form.get("region", "").strip()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            password_confirm = request.form.get("password_confirm", "")

            if not user_id or not name or not password:
                flash("User ID, Nama, dan Password wajib diisi.", "error")
                return redirect(url_for("register"))

            if password != password_confirm:
                flash("Password dan konfirmasi password tidak sama.", "error")
                return redirect(url_for("register"))

            if get_user(user_id):
                flash("User ID sudah terdaftar.", "error")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)

            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO users (user_id, name, birth_date, region, phone, password_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, birth_date, region, phone, password_hash),
            )
            conn.commit()
            conn.close()

            flash("Registrasi berhasil! Silakan login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user_id = request.form.get("user_id", "").strip()
            password = request.form.get("password", "")

            user = get_user(user_id)
            if not user or not user["password_hash"]:
                flash("User ID atau password salah.", "error")
                return redirect(url_for("login"))

            if not check_password_hash(user["password_hash"], password):
                flash("User ID atau password salah.", "error")
                return redirect(url_for("login"))

            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["user_region"] = user["region"]
            flash(f"Selamat datang, {user['name']}!", "success")
            return redirect(url_for("index"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Anda sudah logout.", "success")
        return redirect(url_for("index"))
