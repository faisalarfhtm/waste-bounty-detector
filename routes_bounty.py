import os
import json
from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from db import get_db_connection
from utils import (
    allowed_file,
    calculate_base_points,
    haversine_m,
    get_total_points_for_user,
    current_user,
)
from ml import model


def init_bounty_routes(app):
    """
    Inisialisasi semua route yang berhubungan dengan bounty.
    Fungsi ini dipanggil dari app.py:  init_bounty_routes(app)
    """

    # ---------- Home / Index ----------
    @app.route("/", methods=["GET"])
    def index():
        user = current_user()
        total_points = get_total_points_for_user(user["user_id"]) if user else 0

        # TODO: nanti bisa diganti query beneran ke database
        active_bounties_count = 0
        total_cleaned_locations = 0
        community_users_count = 0

        return render_template(
            "index.html",
            total_points=total_points,
            active_bounties_count=active_bounties_count,
            total_cleaned_locations=total_cleaned_locations,
            community_users_count=community_users_count,
        )

    # ---------- Route lain kamu TARUH DI BAWAH SINI ----------
    # contoh (jangan hapus kalau kamu sudah punya):
    #
    # @app.route("/bounties", methods=["GET"])
    # def list_bounties():
    #     ...
    #
    # @app.route("/bounties/upload", methods=["GET", "POST"])
    # def upload_bounty():
    #     ...
    #
    # dst...
