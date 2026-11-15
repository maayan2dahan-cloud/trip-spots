"""
מעדכן את מסד הנתונים לגלריה של תמונות וסרטונים לכל מקום:
  - בטבלת media נוספת עמודה section:
        "place"      = תמונות וסרטונים של המקום (הגלריה בחלון)
        "directions" = תמונות וסרטונים של הדרך (בדף הוראות הגעה)
  - התמונה הראשית הישנה של כל מקום עוברת להיות התמונה הראשונה בגלריה
אפשר להריץ כמה פעמים - הסקריפט בודק מה כבר קיים.
"""
import sqlite3

conn = sqlite3.connect("places.db")

media_columns = [row[1] for row in conn.execute("PRAGMA table_info(media)")]
if "section" not in media_columns:
    conn.execute("ALTER TABLE media ADD COLUMN section TEXT NOT NULL DEFAULT 'directions'")

# מעבירים את התמונה הראשית הישנה לגלריה
moved = 0
for place_id, image in conn.execute("SELECT id, image FROM places WHERE image IS NOT NULL AND image != ''").fetchall():
    conn.execute("INSERT INTO media (place_id, filename, kind, section) VALUES (?, ?, 'image', 'place')",
                 (place_id, image))
    conn.execute("UPDATE places SET image = NULL WHERE id = ?", (place_id,))
    moved += 1

conn.commit()
conn.close()
print(f"מסד הנתונים עודכן לגלריה! ({moved} תמונות ראשיות עברו לגלריה)")