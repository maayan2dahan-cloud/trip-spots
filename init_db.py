import csv
import sqlite3

# חיבור למסד הנתונים (אם הקובץ לא קיים, הוא נוצר)
conn = sqlite3.connect("places.db")
cur = conn.cursor()

# יצירת הטבלה (מוחקים קודם טבלה ישנה אם יש)
cur.execute("DROP TABLE IF EXISTS places")
cur.execute("""
CREATE TABLE places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    description TEXT,
    instagram TEXT,
    parking TEXT,
    crowded TEXT,
    walk_minutes INTEGER
)
""")

# קריאת ה-CSV והכנסת כל שורה לטבלה
with open("places.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("""
            INSERT INTO places (name, type, lat, lng, description, instagram, parking, crowded, walk_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["name"], row["type"],
            float(row["lat"]), float(row["lng"]),
            row["description"], row["instagram"],
            row["parking"], row["crowded"],
            int(row["walk_minutes"]) if row["walk_minutes"] else None
        ))

conn.commit()   # שמירה
conn.close()
print("מסד הנתונים נוצר!")
