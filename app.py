import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

def get_places():
    conn = sqlite3.connect("places.db")
    conn.row_factory = sqlite3.Row   # כדי לקבל שורות עם שמות עמודות
    rows = conn.execute("SELECT * FROM places").fetchall()
    conn.close()
    return [dict(row) for row in rows]

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

@app.route("/")
def home():
    return render_template("index.html", places=get_places())

@app.route("/add", methods=["GET", "POST"])
def add_place():
    if request.method == "POST":
        location = parse_location(request.form["location"])
        if location is None:
            return render_template("add.html",
                error="לא הצלחתי למצוא קואורדינטות. נסי להדביק את המספרים מגוגל מפות (קליק ימני על המקום).")

        lat, lng = location
        walk = request.form["walk_minutes"]

        conn = sqlite3.connect("places.db")
        conn.execute("""
            INSERT INTO places (name, type, lat, lng, description, instagram, parking, crowded, walk_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["name"], request.form["type"], lat, lng,
            request.form["description"], request.form["instagram"],
            request.form["parking"], request.form["crowded"],
            int(walk) if walk else None
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("add.html")

if __name__ == "__main__":
    app.run(debug=True)