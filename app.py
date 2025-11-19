import os
from flask import Flask
from db import init_db
from routes_auth import init_auth_routes
from routes_bounty import init_bounty_routes

def create_app():
    app = Flask(__name__)
    app.secret_key = "super-secret-key"  # ganti di produksi

    # konfigurasi folder
    app.config["UPLOAD_FOLDER"] = os.path.join("static", "upload")
    app.config["RESULT_FOLDER"] = os.path.join("static", "image", "result")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)

    # inisialisasi DB (buat tabel kalau belum ada)
    init_db()

    # daftarkan routes (auth + bounty)
    init_auth_routes(app)
    init_bounty_routes(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
