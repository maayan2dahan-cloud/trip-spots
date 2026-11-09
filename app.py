from flask import Flask, render_template

app = Flask(__name__)

places = [
    {
        "name": "נהר הירדן",
        "lat": 33.04826822089276,
        "lng":  35.62750630230458,
        "description": "נקודה יפה על הירדן שיש בה מקום נוח לרדת למים",
        "instagram": "",
        "parking": True,
        "crowded": "בסמפטמבר היה ריק",
        "walk_minutes": 0,
    },
    {
        "name": "הלגונה בדפנה",
        "lat": 33.241218526699804, 
        "lng": 35.64410333113514,
        "description": "חניה ללגונה בשדות",
        "instagram": "",
        "parking": True,
        "crowded": "בינוני",
        "walk_minutes": 5,
    },
]

@app.route("/")
def home():
    return render_template("index.html", places=places)

if __name__ == "__main__":
    app.run(debug=True)