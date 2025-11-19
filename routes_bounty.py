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
    # Helper: ambil riwayat redeem poin user
    def _get_user_redemptions(user_id):
        if not user_id:
            return []
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT id, wallet_type, full_name, phone, points, amount, status, requested_at
            FROM reward_redemptions
            WHERE user_id = ?
            ORDER BY datetime(requested_at) DESC
            LIMIT 10
            """,
            (user_id,),
        ).fetchall()
        conn.close()
        return rows

    @app.route("/", methods=["GET"])
    def index():
        user = current_user()
        total_points = get_total_points_for_user(user["user_id"]) if user else 0
        redemptions = _get_user_redemptions(user["user_id"]) if user else []

        return render_template(
            "index.html",
            total_points=total_points,
            last_points=None,
            detections=[],
            image_url=None,
            user=user,
            just_created_bounty=None,
            redemptions=redemptions,
        )


    # ---------- Report Bounty ----------
    @app.route("/submit", methods=["POST"])
    def report_bounty():
        user = current_user()
        if not user:
            flash(
                "Silakan login terlebih dahulu sebelum melaporkan tumpukan sampah.",
                "error",
            )
            return redirect(url_for("login"))

        # ambil koordinat dari form
        lat_str = request.form.get("latitude", "").strip()
        lon_str = request.form.get("longitude", "").strip()
        if not lat_str or not lon_str:
            flash(
                'Lokasi belum terisi. Klik tombol "Gunakan lokasi saya" dan izinkan akses lokasi.',
                "error",
            )
            return redirect(url_for("index"))

        try:
            latitude = float(lat_str)
            longitude = float(lon_str)
        except ValueError:
            flash("Format latitude/longitude tidak valid.", "error")
            return redirect(url_for("index"))

        if "file" not in request.files:
            flash("Tidak ada file gambar di request.", "error")
            return redirect(url_for("index"))

        file = request.files["file"]
        if file.filename == "":
            flash("Tidak ada file yang dipilih.", "error")
            return redirect(url_for("index"))

        if not allowed_file(file.filename):
            flash("Format file tidak didukung. Gunakan PNG/JPG/JPEG.", "error")
            return redirect(url_for("index"))

        # simpan BEFORE image
        ext = file.filename.rsplit(".", 1)[1].lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        before_filename = f"before_{timestamp}.{ext}"
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], before_filename)
        file.save(upload_path)

        # YOLO pada BEFORE
        results = model.predict(upload_path, imgsz=736, save=False)
        result = results[0]

        detections = []
        if result.boxes is not None and len(result.boxes) > 0:
            classes = result.boxes.cls.tolist()
            scores = result.boxes.conf.tolist()
            for cls_id, conf in zip(classes, scores):
                cls_id = int(cls_id)
                label = result.names.get(cls_id, str(cls_id))
                detections.append(
                    {"label": label, "confidence": round(float(conf) * 100, 2)}
                )

        if not detections:
         flash(
             "Tidak ada sampah yang terdeteksi pada gambar. "
             "Bounty tidak dibuat dan tidak ada reward yang diberikan. "
             "Silakan upload foto tumpukan sampah yang lebih jelas.",
             "error",
         )
         total_points = get_total_points_for_user(user["user_id"])
         redemptions = _get_user_redemptions(user["user_id"])
         return render_template(
             "index.html",
             total_points=total_points,
             last_points=0,
             detections=[],
             image_url=None,
             user=user,
             just_created_bounty=None,
             redemptions=redemptions,
         )


        base_points = calculate_base_points(detections)
        points_reporter = base_points
        points_cleaner = base_points * 2

        # gambar annotated (untuk tampilan)
        annotated_img = result.plot()
        annotated_filename = f"before_annotated_{timestamp}.{ext}"
        annotated_path = os.path.join(
            app.config["RESULT_FOLDER"], annotated_filename
        )

        try:
            from PIL import Image

            img_rgb = annotated_img[..., ::-1]
            Image.fromarray(img_rgb).save(annotated_path)
        except Exception as e:
            print("Gagal menyimpan gambar hasil deteksi:", e)
            annotated_filename = None

        location_text = user["region"] or ""

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO bounties (
                reporter_id, location, latitude, longitude, created_at,
                claimed_at, completed_at,
                before_image, after_image, status,
                num_objects, points_reporter, points_cleaner, labels_json
            )
            VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, NULL, 'OPEN',
                    ?, ?, ?, ?)
            """,
            (
                user["user_id"],
                location_text,
                latitude,
                longitude,
                timestamp,
                before_filename,
                len(detections),
                points_reporter,
                points_cleaner,
                json.dumps(detections, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()

        total_points = get_total_points_for_user(user["user_id"])
        redemptions = _get_user_redemptions(user["user_id"])

        image_url = None
        if annotated_filename:
            image_url = url_for(
                "static", filename=f"image/result/{annotated_filename}"
            )

        flash(
            f"Bounty berhasil dibuat! Potensi poin: uploader {points_reporter}, cleaner {points_cleaner}.",
            "success",
        )

        return render_template(
            "index.html",
            total_points=total_points,
            last_points=None,
            detections=detections,
            image_url=image_url,
            user=user,
            just_created_bounty={
                "points_reporter": points_reporter,
                "points_cleaner": points_cleaner,
            },
            redemptions=redemptions,
        )
    # ---------- Halaman Reward ----------
    @app.route("/rewards", methods=["GET"])
    def rewards_page():
        user = current_user()
        if not user:
            flash("Silakan login terlebih dahulu untuk mengakses menu reward.", "error")
            return redirect(url_for("login"))

        total_points = get_total_points_for_user(user["user_id"])
        redemptions = _get_user_redemptions(user["user_id"])

        return render_template(
            "rewards.html",
            user=user,
            total_points=total_points,
            redemptions=redemptions,
        )

    # ---------- Redeem Reward ----------
    @app.route("/rewards/redeem", methods=["POST"])
    def redeem_points():
        user = current_user()
        if not user:
            flash("Silakan login untuk menukar poin.", "error")
            return redirect(url_for("login"))

        wallet_type = (request.form.get("wallet_type") or "").upper()
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        amount_str = (request.form.get("amount") or "").strip()

        allowed_wallets = ["GOPAY", "DANA", "OVO", "SHOPEEPAY", "LINKAJA", "SAKUKU"]

        if wallet_type not in allowed_wallets:
            flash("Pilih jenis e-wallet yang valid.", "error")
            return redirect(url_for("rewards_page"))

        if not full_name:
            flash("Nama penerima tidak boleh kosong.", "error")
            return redirect(url_for("rewards_page"))

        if not phone:
            flash("Nomor HP e-wallet tidak boleh kosong.", "error")
            return redirect(url_for("rewards_page"))

        total_points = get_total_points_for_user(user["user_id"])

        if total_points <= 0:
            flash("Poin kamu belum cukup untuk diredeem.", "error")
            return redirect(url_for("rewards_page"))

        if amount_str:
            try:
                amount = int(amount_str)
            except ValueError:
                flash("Jumlah poin yang ingin ditukar harus berupa angka.", "error")
                return redirect(url_for("rewards_page"))
        else:
            # kalau kosong, redeem semua poin
            amount = total_points

        if amount <= 0:
            flash("Jumlah poin yang ingin ditukar harus lebih dari 0.", "error")
            return redirect(url_for("rewards_page"))

        if amount > total_points:
            flash("Jumlah poin yang ingin ditukar melebihi saldo poin kamu.", "error")
            return redirect(url_for("rewards_page"))

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO reward_redemptions
                (user_id, wallet_type, full_name, phone, points, amount, status, requested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["user_id"],
                wallet_type,
                full_name,
                phone,
                amount,
                amount,  # 1 poin = Rp 1
                "PENDING",
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        flash(
            "Permintaan redeem berhasil dibuat. "
            "Reward akan dikirim maksimal 24 jam ke e-wallet yang kamu pilih.",
            "success",
        )
        return redirect(url_for("rewards_page"))


    # ---------- List Bounty (OPEN + CLAIMED) ----------
    @app.route("/bounties", methods=["GET"])
    def bounty_list():
        user = current_user()
        if not user:
            flash(
                "Silakan login terlebih dahulu untuk melihat bounty.",
                "error",
            )
            return redirect(url_for("login"))

        user_lat = request.args.get("lat", type=float)
        user_lon = request.args.get("lon", type=float)

        conn = get_db_connection()

        # bounty OPEN untuk radius 100 m
        open_rows = conn.execute(
            """
            SELECT b.*, u.name AS reporter_name
            FROM bounties b
            JOIN users u ON b.reporter_id = u.user_id
            WHERE b.status = 'OPEN' AND b.reporter_id != ?
            """,
            (user["user_id"],),
        ).fetchall()

        # bounty CLAIMED oleh user ini (sedang dikerjakan)
        my_claimed_rows = conn.execute(
            """
            SELECT b.*, u.name AS reporter_name
            FROM bounties b
            JOIN users u ON b.reporter_id = u.user_id
            WHERE b.status = 'CLAIMED' AND b.cleaner_id = ?
            ORDER BY b.claimed_at DESC
            """,
            (user["user_id"],),
        ).fetchall()

        conn.close()

        open_bounties = []
        if user_lat is not None and user_lon is not None:
            for r in open_rows:
                lat = r["latitude"]
                lon = r["longitude"]
                if lat is None or lon is None:
                    continue
                dist_m = haversine_m(user_lat, user_lon, lat, lon)
                if dist_m <= 100.0:
                    d = dict(r)
                    d["distance_m"] = dist_m
                    open_bounties.append(d)
            open_bounties.sort(key=lambda x: x["distance_m"])
        else:
            open_bounties = []

        my_claimed = [dict(r) for r in my_claimed_rows]

        return render_template(
            "bounties.html",
            user=user,
            open_bounties=open_bounties,
            my_claimed=my_claimed,
            user_lat=user_lat,
            user_lon=user_lon,
        )

    # ---------- Claim Bounty ----------
    @app.route("/bounty/<int:bounty_id>/claim", methods=["POST"])
    def bounty_claim(bounty_id):
        user = current_user()
        if not user:
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("login"))

        user_lat = request.args.get("lat", type=float)
        user_lon = request.args.get("lon", type=float)

        conn = get_db_connection()
        bounty = conn.execute(
            "SELECT * FROM bounties WHERE id = ?", (bounty_id,)
        ).fetchone()

        if not bounty:
            conn.close()
            flash("Bounty tidak ditemukan.", "error")
            return redirect(url_for("bounty_list"))

        if bounty["reporter_id"] == user["user_id"]:
            conn.close()
            flash("Tidak bisa mengambil bounty yang kamu buat sendiri.", "error")
            return redirect(url_for("bounty_list"))

        if bounty["status"] != "OPEN":
            conn.close()
            flash("Bounty sudah diambil atau selesai.", "error")
            return redirect(url_for("bounty_list"))

        # cek radius 100 m
        if (
            user_lat is None
            or user_lon is None
            or bounty["latitude"] is None
            or bounty["longitude"] is None
        ):
            conn.close()
            flash("Lokasi tidak lengkap, tidak bisa mengambil bounty.", "error")
            return redirect(url_for("bounty_list"))

        dist_m = haversine_m(
            user_lat, user_lon, bounty["latitude"], bounty["longitude"]
        )
        if dist_m > 100.0:
            conn.close()
            flash(
                "Jarakmu lebih dari 100 meter dari lokasi bounty.",
                "error",
            )
            return redirect(url_for("bounty_list"))

        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        conn.execute(
            """
            UPDATE bounties
            SET cleaner_id = ?, status = 'CLAIMED', claimed_at = ?
            WHERE id = ?
            """,
            (user["user_id"], now, bounty_id),
        )
        conn.commit()
        conn.close()

        flash(
            "Bounty berhasil kamu ambil. Bersihkan dan upload foto AFTER.",
            "success",
        )
        return redirect(url_for("bounty_complete", bounty_id=bounty_id))

    # ---------- Complete Bounty ----------
    @app.route("/bounty/<int:bounty_id>/complete", methods=["GET", "POST"])
    def bounty_complete(bounty_id):
        user = current_user()
        if not user:
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("login"))

        conn = get_db_connection()
        bounty = conn.execute(
            "SELECT * FROM bounties WHERE id = ?", (bounty_id,)
        ).fetchone()
        conn.close()

        if not bounty:
            flash("Bounty tidak ditemukan.", "error")
            return redirect(url_for("bounty_list"))

        if bounty["cleaner_id"] != user["user_id"]:
            flash("Bounty ini bukan milikmu sebagai cleaner.", "error")
            return redirect(url_for("bounty_list"))

        if bounty["status"] == "COMPLETED":
            flash("Bounty ini sudah selesai.", "info")
            return redirect(url_for("bounty_list"))

        if request.method == "POST":
            # 1. validasi lokasi AFTER
            lat_str = request.form.get("latitude", "").strip()
            lon_str = request.form.get("longitude", "").strip()
            if not lat_str or not lon_str:
                flash(
                    'Lokasi AFTER belum terisi. Klik "Gunakan lokasi saya" dan izinkan akses lokasi.',
                    "error",
                )
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            try:
                lat_after = float(lat_str)
                lon_after = float(lon_str)
            except ValueError:
                flash("Format latitude/longitude AFTER tidak valid.", "error")
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            if bounty["latitude"] is None or bounty["longitude"] is None:
                flash(
                    "Lokasi bounty tidak lengkap, tidak bisa diverifikasi.",
                    "error",
                )
                return redirect(url_for("bounty_list"))

            dist_m = haversine_m(
                lat_after, lon_after, bounty["latitude"], bounty["longitude"]
            )
            if dist_m > 100.0:
                flash(
                    f"Posisimu sekarang terlalu jauh dari lokasi bounty (≈ {dist_m:.1f} m). "
                    "Tidak bisa menyelesaikan bounty.",
                    "error",
                )
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            # 2. validasi gambar AFTER (tidak boleh masih ada sampah)
            if "file" not in request.files:
                flash("Tidak ada file AFTER yang diupload.", "error")
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            file = request.files["file"]
            if file.filename == "":
                flash("Tidak ada file yang dipilih.", "error")
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            if not allowed_file(file.filename):
                flash("Format file tidak didukung.", "error")
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            ext = file.filename.rsplit(".", 1)[1].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            after_filename = f"after_{timestamp}.{ext}"
            after_path = os.path.join(app.config["UPLOAD_FOLDER"], after_filename)
            file.save(after_path)

            # YOLO untuk AFTER
            results_after = model.predict(after_path, imgsz=736, save=False)
            result_after = results_after[0]

            after_detections = []
            if result_after.boxes is not None and len(result_after.boxes) > 0:
                classes = result_after.boxes.cls.tolist()
                scores = result_after.boxes.conf.tolist()
                for cls_id, conf in zip(classes, scores):
                    cls_id = int(cls_id)
                    label = result_after.names.get(cls_id, str(cls_id))
                    after_detections.append(
                        {
                            "label": label,
                            "confidence": round(float(conf) * 100, 2),
                        }
                    )

            if after_detections:
                flash(
                    "Sistem masih mendeteksi objek sampah pada foto AFTER. "
                    "Bounty belum bisa diselesaikan. Bersihkan lagi dan upload ulang.",
                    "error",
                )
                return redirect(url_for("bounty_complete", bounty_id=bounty_id))

            # kalau lolos semua, tandai COMPLETED
            now = datetime.now().strftime("%Y%m%d_%H%M%S")

            conn = get_db_connection()
            conn.execute(
                """
                UPDATE bounties
                SET after_image = ?, status = 'COMPLETED', completed_at = ?
                WHERE id = ?
                """,
                (after_filename, now, bounty_id),
            )
            conn.commit()
            conn.close()

            flash(
                f"Bounty selesai! Kamu mendapatkan {bounty['points_cleaner']} poin sebagai cleaner.",
                "success",
            )
            return redirect(url_for("index"))

        # GET: tampilkan halaman complete
        before_url = url_for("static", filename=f"upload/{bounty['before_image']}")

        return render_template(
            "complete_bounty.html",
            user=user,
            bounty=bounty,
            before_url=before_url,
        )
