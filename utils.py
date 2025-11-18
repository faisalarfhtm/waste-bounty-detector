import math
from flask import session
from db import get_db_connection


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "png",
        "jpg",
        "jpeg",
    }


def calculate_base_points(detections):
    """
    Hitung poin dasar dari list detections.
    """
    score_map = {
        "PET_Bottles": 3,
        "Aluminium_Cans": 3,
        "HDPE_Milk_Bottles": 2,
    }
    total = 0
    for det in detections:
        total += score_map.get(det["label"], 1)
    return total


def haversine_m(lat1, lon1, lat2, lon2):
    """
    Hitung jarak (meter) antara dua titik lat/lon.
    """
    R = 6371000.0  # radius bumi dalam meter
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2.0
    ) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_total_points_for_user(user_id: str | None):
    if not user_id:
        return 0
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(
                CASE WHEN reporter_id = ? THEN points_reporter ELSE 0 END
            ), 0)
            +
            COALESCE(SUM(
                CASE WHEN cleaner_id = ? THEN points_cleaner ELSE 0 END
            ), 0)
            AS total_points
        FROM bounties
        WHERE status = 'COMPLETED'
        """,
        (user_id, user_id),
    ).fetchone()
    conn.close()
    return row["total_points"] if row else 0


def get_user(user_id: str):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_user(uid)
