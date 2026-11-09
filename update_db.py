import sqlite3

conn = sqlite3.connect("places.db")

# בודקים אילו עמודות כבר קיימות בטבלה
columns = [row[1] for row in conn.execute("PRAGMA table_info(places)")]

if "image" not in columns:
    conn.execute("ALTER TABLE places ADD COLUMN image TEXT")

if "visited" not in columns:
    conn.execute("ALTER TABLE places ADD COLUMN visited TEXT")
    conn.execute("UPDATE places SET visited = 'ביקרתי'")   # בכל הקיימים ביקרתי

conn.commit()
conn.close()
print("מסד הנתונים עודכן!")