import os
import re
import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # עד 300MB בשליחה אחת (בגלל סרטונים)

UPLOAD_FOLDER = os.path.join("static", "uploads")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TYPES = ["מעיין", "תצפית", "מסלול", "נחל", "אחר"]
LOCATION_ERROR = "לא הצלחתי למצוא קואורדינטות. נסי להדביק את המספרים מגוגל מפות (קליק ימני על המקום)."


# ---------- פונקציות עזר ----------

def get_db():
    conn = sqlite3.connect("places.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_places():
    """כל המקומות, וגם כמה תמונות/סרטונים של הדרך יש לכל אחד"""
    conn = get_db()
    rows = conn.execute("""
        SELECT places.*,
               (SELECT COUNT(*) FROM media WHERE media.place_id = places.id) AS media_count
        FROM places
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_place(place_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_media(place_id):
    """התמונות והסרטונים של הדרך למקום מסוים"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM media WHERE place_id = ? ORDER BY id", (place_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_file(filename):
    if filename:
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)

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

def file_kind(filename):
    """מחזירה "image", "video" או None לפי סיומת הקובץ"""
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return None

def save_upload(file):
    """שומרת קובץ שהועלה בשם אקראי ומחזירה את השם החדש"""
    ext = os.path.splitext(file.filename)[1].lower()
    name = uuid.uuid4().hex + ext
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return name

def check_uploads():
    """בודקת את כל הקבצים שהועלו לפני ששומרים משהו. מחזירה שגיאה או None"""
    image = request.files.get("image")
    if image and image.filename and file_kind(image.filename) != "image":
        return "התמונה הראשית חייבת להיות תמונה (jpg, png, webp, gif)."
    for f in request.files.getlist("media"):
        if f and f.filename and file_kind(f.filename) is None:
            return f"הקובץ {f.filename} לא נתמך. אפשר להעלות תמונות או סרטונים (mp4, mov, webm)."
    return None

def save_media_files(conn, place_id):
    """שומרת את כל התמונות והסרטונים של הדרך שהועלו, ומקשרת אותם למקום"""
    for f in request.files.getlist("media"):
        if f and f.filename:
            conn.execute("INSERT INTO media (place_id, filename, kind) VALUES (?, ?, ?)",
                         (place_id, save_upload(f), file_kind(f.filename)))

def read_form():
    """קוראת את שדות הטופס. מחזירה (מילון עם הנתונים, שגיאה)"""
    location = parse_location(request.form["location"])
    if location is None:
        return None, LOCATION_ERROR
    error = check_uploads()
    if error:
        return None, error
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
        "directions": request.form["directions"],
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
        if error:
            # מחזירים את הטופס עם מה שכבר הוקלד
            return render_template("add.html", error=error, place=request.form, types=TYPES, media=[])

        image = request.files.get("image")
        data["image"] = save_upload(image) if image and image.filename else None

        conn = get_db()
        cur = conn.execute("""
            INSERT INTO places (name, type, lat, lng, description, instagram,
                                parking, crowded, walk_minutes, image, visited, directions)
            VALUES (:name, :type, :lat, :lng, :description, :instagram,
                    :parking, :crowded, :walk_minutes, :image, :visited, :directions)
        """, data)
        save_media_files(conn, cur.lastrowid)   # lastrowid = ה-id של המקום החדש
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("add.html", place={}, types=TYPES, media=[])


@app.route("/edit/<int:place_id>", methods=["GET", "POST"])
def edit_place(place_id):
    place = get_place(place_id)
    if place is None:
        return "המקום לא נמצא", 404

    if request.method == "POST":
        data, error = read_form()
        if error:
            form = dict(request.form)
            form["image"] = place["image"]
            return render_template("add.html", error=error, place=form, types=TYPES,
                                   editing=True, media=get_media(place_id))

        # תמונה ראשית חדשה? מוחקים את הישנה
        image = request.files.get("image")
        if image and image.filename:
            delete_file(place["image"])
            data["image"] = save_upload(image)
        else:
            data["image"] = place["image"]
        data["id"] = place_id

        conn = get_db()
        conn.execute("""
            UPDATE places
            SET name = :name, type = :type, lat = :lat, lng = :lng,
                description = :description, instagram = :instagram,
                parking = :parking, crowded = :crowded,
                walk_minutes = :walk_minutes, image = :image, visited = :visited,
                directions = :directions
            WHERE id = :id
        """, data)

        # קבצים שסימנו ב-✕ למחיקה
        for media_id in request.form.getlist("remove_media"):
            row = conn.execute("SELECT filename FROM media WHERE id = ? AND place_id = ?",
                               (media_id, place_id)).fetchone()
            if row:
                delete_file(row["filename"])
                conn.execute("DELETE FROM media WHERE id = ?", (media_id,))

        save_media_files(conn, place_id)
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    place["location"] = f"{place['lat']}, {place['lng']}"
    return render_template("add.html", place=place, types=TYPES, editing=True, media=get_media(place_id))


@app.route("/directions/<int:place_id>")
def directions(place_id):
    place = get_place(place_id)
    if place is None:
        return "המקום לא נמצא", 404
    return render_template("directions.html", place=place, media=get_media(place_id))


@app.route("/delete/<int:place_id>", methods=["POST"])
def delete_place(place_id):
    place = get_place(place_id)
    if place is None:
        return "המקום לא נמצא", 404

    conn = get_db()
    # מוחקים את כל הקבצים: התמונה הראשית + התמונות והסרטונים של הדרך
    delete_file(place["image"])
    for row in conn.execute("SELECT filename FROM media WHERE place_id = ?", (place_id,)).fetchall():
        delete_file(row["filename"])
    conn.execute("DELETE FROM media WHERE place_id = ?", (place_id,))
    conn.execute("DELETE FROM places WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)