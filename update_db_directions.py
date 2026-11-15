"""
מוסיף למסד הנתונים את מה שצריך להוראות הגעה:
  - עמודה directions (הסבר בטקסט) בטבלת places
  - טבלה חדשה media (תמונות וסרטונים של הדרך, כמה לכל מקום)
אפשר להריץ כמה פעמים - הסקריפט בודק מה כבר קיים.
"""
import sqlite3

conn = sqlite3.connect("places.db")

columns = [row[1] for row in conn.execute("PRAGMA table_info(places)")]
if "directions" not in columns:
    conn.execute("ALTER TABLE places ADD COLUMN directions TEXT")

conn.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id INTEGER NOT NULL,      -- לאיזה מקום הקובץ שייך
        filename TEXT NOT NULL,         -- שם הקובץ בתיקייה static/uploads
        kind TEXT NOT NULL              -- "image" או "video"
    )
""")

conn.commit()
conn.close()
print("מסד הנתונים עודכן להוראות הגעה!")