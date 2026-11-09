import os
import re
import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # עד 10MB לתמונה

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TYPES = ["מעיין", "תצפית", "מסלול", "נחל", "אחר"]
LOCATION_ERROR = "לא הצלחתי למצוא קואורדינטות. נסי להדביק את המספרים מגוגל מפות (קליק ימני על המקום)."


# ---------- פונקציות עזר ----------

def get_db():
    conn = sqlite3.connect("places.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_places():
    conn = get_db()
    rows = conn.execute("SELECT * FROM places").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_place(place_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def parse_location(text):
    """מקבלת קואורדינטות או קישור של גוגל מפות ומחזירה (lat, lng), או None"""
    patterns = [
        r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",   # המיקום המדויק של מקום בקישור
        r"@(-?\d+\.\d+),(-?\d+\.\d+)",       # מרכז המפה בקישור
        r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)",  # "32.123, 35.456"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1)), float(match.group(2))
    return None

def save_image(file):
    """שומרת תמונה שהועלתה. מחזירה (שם קובץ, שגיאה)"""
    if not file or not file.filename:
        return None, None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, "אפשר להעלות רק תמונות (jpg, png, webp, gif)."
    name = uuid.uuid4().hex + ext
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return name, None

def read_form():
    """קוראת את שדות הטופס. מחזירה (מילון עם הנתונים, שגיאה)"""
    location = parse_location(request.form["location"])
    if location is None:
        return None, LOCATION_ERROR
    walk = request.form["walk_minutes"]
    data = {
        "name": request.form["name"],
        "type": request.form["type"],
        "lat": location[0],
        "lng": location[1],
        "description": request.form["description"],
        "instagram": request.form["instagram"],
        "parking": request.form["parking"],
        "crowded": request.form["crowded"],
        "walk_minutes": int(walk) if walk else None,
        "visited": request.form["visited"],
    }
    return data, None


# ---------- דפים ----------

@app.route("/")
def home():
    return render_template("index.html", places=get_places())


@app.route("/add", methods=["GET", "POST"])
def add_place():
    if request.method == "POST":
        data, error = read_form()
        if error is None:
            data["image"], error = save_image(request.files.get("image"))
        if error:
            # מחזירים את הטופס עם מה שכבר הוקלד
            return render_template("add.html", error=error, place=request.form, types=TYPES)

        conn = get_db()
        conn.execute("""
            INSERT INTO places (name, type, lat, lng, description, instagram,
                                parking, crowded, walk_minutes, image, visited)
            VALUES (:name, :type, :lat, :lng, :description, :instagram,
                    :parking, :crowded, :walk_minutes, :image, :visited)
        """, data)
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("add.html", place={}, types=TYPES)


@app.route("/edit/<int:place_id>", methods=["GET", "POST"])
def edit_place(place_id):
    place = get_place(place_id)
    if place is None:
        return "המקום לא נמצא", 404

    if request.method == "POST":
        data, error = read_form()
        new_image = None
        if error is None:
            new_image, error = save_image(request.files.get("image"))
        if error:
            form = dict(request.form)
            form["image"] = place["image"]
            return render_template("add.html", error=error, place=form, types=TYPES, editing=True)

        # אם הועלתה תמונה חדשה - מוחקים את הישנה
        if new_image and place["image"]:
            old_path = os.path.join(UPLOAD_FOLDER, place["image"])
            if os.path.exists(old_path):
                os.remove(old_path)

        data["image"] = new_image or place["image"]   # בלי תמונה חדשה - שומרים את הישנה
        data["id"] = place_id

        conn = get_db()
        conn.execute("""
            UPDATE places
            SET name = :name, type = :type, lat = :lat, lng = :lng,
                description = :description, instagram = :instagram,
                parking = :parking, crowded = :crowded,
                walk_minutes = :walk_minutes, image = :image, visited = :visited
            WHERE id = :id
        """, data)
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    place["location"] = f"{place['lat']}, {place['lng']}"
    return render_template("add.html", place=place, types=TYPES, editing=True)


if __name__ == "__main__":
    app.run(debug=True)