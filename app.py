import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

def get_places():
    conn = sqlite3.connect("places.db")
    conn.row_factory = sqlite3.Row   # כדי לקבל שורות עם שמות עמודות
    rows = conn.execute("SELECT * FROM places").fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.route("/")
def home():
    return render_template("index.html", places=get_places())

if __name__ == "__main__":
    app.run(debug=True)