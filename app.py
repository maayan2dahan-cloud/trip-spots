from flask import Flask, render_template

app = Flask(__name__)

places = [
    {
        "name": "עין חניה",
        "lat": 31.7428,
        "lng": 35.1617,
        "description": "מעיין עם בריכות ומבנים עתיקים, קרוב לירושלים.",
        "instagram": "",
        "parking": True,
        "crowded": "עמוס בסופ\"ש",
        "walk_minutes": 5,
    },
    {
        "name": "מפל הבניאס",
        "lat": 33.2378,
        "lng": 35.6303,
        "description": "המפל הכי חזק בארץ, מסלול קצר ויפה.",
        "instagram": "",
        "parking": True,
        "crowded": "בינוני",
        "walk_minutes": 20,
    },
]

@app.route("/")
def home():
    return render_template("index.html", places=places)

if __name__ == "__main__":
    app.run(debug=True)