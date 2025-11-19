import os
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# Twilio optional – kalau tidak mau pakai, import ini boleh dihapus
from twilio.rest import Client

from utils import get_user
from db import get_db_connection


def send_whatsapp_message(phone: str, text: str):
    """
    Kirim pesan informasi ke WhatsApp (opsional).
    phone harus sudah termasuk kode negara, misal: +62812xxxxxxx

    Konfigurasi via environment variable:
      - TWILIO_ACCOUNT_SID
      - TWILIO_AUTH_TOKEN
      - TWILIO_WHATSAPP_FROM  (contoh: 'whatsapp:+14155238886')

    Kalau belum dikonfigurasi atau gagal kirim, fungsi ini TIDAK akan melempar error
    (supaya pendaftaran tetap jalan).
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_WHATSAPP_FROM")

    # Kalau belum diset, cukup print ke console dan selesai
    if not all([account_sid, auth_token, from_whatsapp]):
        print("=== WhatsApp (SIMULASI, Twilio belum dikonfigurasi) ===")
        print(f"Nomor: {phone}")
        print(f"Pesan: {text}")
        print("=======================================================")
        return

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            from_=from_whatsapp,
            to=f"whatsapp:{phone}",
            body=text,
        )
    except Exception as e:
        # Jangan menghentikan aplikasi hanya karena WA gagal
        print("[WARN] Gagal mengirim WhatsApp:", e)


def init_auth_routes(app):
    # ---------------- REGISTER ----------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            user_id = request.form.get("user_id", "").strip()
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            birth_date = request.form.get("birth_date", "").strip()
            region = request.form.get("region", "").strip()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            password_confirm = request.form.get("password_confirm", "")

            if not user_id or not name or not password or not phone:
                flash(
                    "User ID, Nama, Password, dan Nomor HP wajib diisi.",
                    "error",
                )
                return redirect(url_for("register"))

            if password != password_confirm:
                flash("Password dan konfirmasi password tidak sama.", "error")
                return redirect(url_for("register"))

            # cek apakah user_id sudah dipakai
            if get_user(user_id):
                flash("User ID sudah terdaftar.", "error")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)

            # simpan user ke DB dengan is_phone_verified = 0 (BELUM diverifikasi)
            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO users
                    (user_id, name, email, birth_date, region,
                     phone, password_hash, is_phone_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    user_id,
                    name,
                    email,
                    birth_date,
                    region,
                    phone,
                    password_hash,
                ),
            )
            conn.commit()
            conn.close()

            # Kirim pesan info ke WhatsApp (opsional, best-effort)
            send_whatsapp_message(
                phone,
                "Terima kasih telah mendaftar Smart Waste Detector. "
                "Nomor WhatsApp Anda saat ini tercatat sebagai BELUM TERVERIFIKASI.",
            )

            flash(
                "Registrasi berhasil! Nomor WhatsApp Anda BELUM terverifikasi, "
                "namun akun sudah aktif dan bisa digunakan.",
                "success",
            )
            return redirect(url_for("login"))

        return render_template("register.html")

    # ---------------- LOGIN ----------------
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

            # Di sini kita TIDAK memblokir user yang belum verifikasi HP.
            # Kita hanya memberi informasi di flash message.
            if "is_phone_verified" in user.keys() and user["is_phone_verified"] == 0:
                flash(
                    "Nomor WhatsApp Anda BELUM terverifikasi. "
                    "Silakan hubungi admin jika ingin melakukan verifikasi.",
                    "info",
                )

            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["user_region"] = user["region"]
            return redirect(url_for("index"))

        return render_template("login.html")

    # ---------------- LOGOUT ----------------
    @app.route("/logout")
    def logout():
        session.clear()
        flash("Anda sudah logout.", "success")
        return redirect(url_for("index"))
