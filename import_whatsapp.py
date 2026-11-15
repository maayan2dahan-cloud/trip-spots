"""
ייבוא מקומות מקובץ ייצוא של צ'אט וואטסאפ.

שני שלבים:
    1. python import_whatsapp.py _chat.txt
       קורא את הצ'אט ויוצר את הקובץ whatsapp_preview.csv (עוד לא שומר כלום במסד)
       -> פותחים את הקובץ ומתקנים שמות וסוגים. שורה שלא רוצים - פשוט מוחקים.
    2. python import_whatsapp.py --save
       מכניס למסד הנתונים את מה שנשאר ב-whatsapp_preview.csv
"""
import csv
import math
import re
import sqlite3
import sys
from datetime import datetime, timedelta

DB_PATH = "places.db"
DUPLICATE_METERS = 300        # מקום קרוב יותר מזה למקום קיים נחשב כפילות
NAME_WINDOW_MINUTES = 5       # כמה זמן לפני/אחרי המיקום מחפשים הודעה עם שם

# ---------- תבניות ----------
HEADER = re.compile(r"^\[(\d{1,2}\.\d{1,2}\.\d{4}), (\d{1,2}:\d{2}:\d{2})\] ([^:]+): ?(.*)$")
GOOGLE = re.compile(r"maps\.google\.com/\?q=(-?\d+\.\d+),(-?\d+\.\d+)")
WAZE_LL = re.compile(r"waze\.com/ul\?ll=(-?\d+\.\d+)(?:,|%2C)(-?\d+\.\d+)")
WAZE_HASH = re.compile(r"waze\.com/ul/h([0-9b-hjkmnp-z]+)")
INSTAGRAM = re.compile(r"https?://(?:www\.)?instagram\.com/\S+")
ANY_LINK = re.compile(r"https?://\S+")
SHORT_LINK = re.compile(r"https?://maps\.app\.goo\.gl/\S+")
INVISIBLE = re.compile("[\u200e\u200f\u202a-\u202e]")   # תווי כיוון נסתרים שוואטסאפ מוסיף
NOISE = ["התמונה הושמטה", "סרטון הווידאו הושמט", "מחקת את ההודעה הזו.", "📍", "מיקום:", "נסיעה עם Waze אל"]


# ---------- קריאת הצ'אט ----------
def read_messages(path):
    """מחזירה רשימה של הודעות: {time, sender, text}. הודעה בכמה שורות מתאחדת להודעה אחת."""
    messages = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = INVISIBLE.sub("", raw.rstrip("\n"))
            match = HEADER.match(line)
            if match:
                date, time, sender, text = match.groups()
                messages.append({
                    "time": datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M:%S"),
                    "sender": sender.strip(),
                    "text": text,
                })
            elif messages:
                messages[-1]["text"] += "\n" + line   # המשך של ההודעה הקודמת
    return messages


# ---------- Geohash (הקידוד שוויז משתמש בו בקישורים קצרים) ----------
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def decode_geohash(geohash):
    """כל תו מצמצם את התחום לחצי, לסירוגין בקו אורך ובקו רוחב."""
    lat, lng = [-90.0, 90.0], [-180.0, 180.0]
    use_lng = True
    for char in geohash:
        bits = BASE32.index(char)
        for mask in (16, 8, 4, 2, 1):
            rng = lng if use_lng else lat
            middle = (rng[0] + rng[1]) / 2
            if bits & mask:
                rng[0] = middle
            else:
                rng[1] = middle
            use_lng = not use_lng
    return (lat[0] + lat[1]) / 2, (lng[0] + lng[1]) / 2


def find_coordinates(text):
    for pattern in (GOOGLE, WAZE_LL):
        match = pattern.search(text)
        if match:
            return float(match.group(1)), float(match.group(2))
    match = WAZE_HASH.search(text)
    if match:
        return decode_geohash(match.group(1))
    return None


# ---------- ניחוש שם וסוג ----------
def clean_text(text):
    text = ANY_LINK.sub("", text)
    for word in NOISE:
        text = text.replace(word, "")
    lines = [l.strip(" :-,") for l in text.split("\n")]
    lines = [l for l in lines if len(l) >= 2]
    return lines[0] if lines else ""

def nearby_captions(messages, i, step, stop_at, claimed):
    """הודעות טקסט של אותו שולח, קרובות בזמן, עד המיקום הבא (step=1) או הקודם (step=-1)."""
    msg = messages[i]
    window = timedelta(minutes=NAME_WINDOW_MINUTES)
    captions = []
    j = i + step
    while 0 <= j < len(messages) and j != stop_at:
        other = messages[j]
        if abs(other["time"] - msg["time"]) > window:
            break
        if other["sender"] == msg["sender"] and j not in claimed:
            text = clean_text(other["text"])
            if text:
                captions.append((j, text))
        j += step
    return captions

def assign_names(messages, coord_indexes):
    """לכל הודעת מיקום: שם + תיאור.
    כיתוב שבא אחרי מיקום שייך לו (ככה רוב ההודעות בקבוצה בנויות),
    ורק אם אין כזה, מחפשים כיתוב שבא לפני המיקום."""
    claimed = set()
    after = {}
    for k, i in enumerate(coord_indexes):
        next_coord = coord_indexes[k + 1] if k + 1 < len(coord_indexes) else len(messages)
        after[i] = nearby_captions(messages, i, 1, next_coord, claimed)
        claimed.update(j for j, _ in after[i])

    result = {}
    for k, i in enumerate(coord_indexes):
        own = clean_text(messages[i]["text"])
        captions = [t for _, t in after[i]]
        if not own and not captions:
            prev_coord = coord_indexes[k - 1] if k > 0 else -1
            before = nearby_captions(messages, i, -1, prev_coord, claimed)
            claimed.update(j for j, _ in before)
            captions = [t for _, t in before]
        names = ([own] if own else []) + captions
        result[i] = (names[0] if names else "", " / ".join(names[1:]))
    return result

def starts_word(name, words):
    """האם אחת המילים מופיעה בתחילת מילה בשם (כדי ש"מודיעין" לא ייחשב "עין")"""
    return any(re.search(r"(^|\s)" + w, name) for w in words)

def guess_type(name):
    if starts_word(name, ["מצפה", "תצפית", "נוף"]):
        return "תצפית"
    if starts_word(name, ["נחל"]):
        return "נחל"
    if starts_word(name, ["עין", "מעיין", "מעין", "מאגר", "בריכ", "מפל", "ירדן", "לגונה", "הלגונה"]):
        return "מעיין"
    return "אחר"


# ---------- מרחק (Haversine) ----------
def distance_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---------- שלב 1: קריאת הצ'אט ויצירת תצוגה מקדימה ----------
PREVIEW = "whatsapp_preview.csv"
FIELDS = ["name", "type", "lat", "lng", "description", "instagram", "visited"]

def preview(chat_path):
    messages = read_messages(chat_path)

    conn = sqlite3.connect(DB_PATH)
    existing = [(r[0], r[1], r[2]) for r in conn.execute("SELECT name, lat, lng FROM places")]
    conn.close()

    coord_indexes = [i for i, m in enumerate(messages) if find_coordinates(m["text"])]
    names = assign_names(messages, coord_indexes)

    new_places, duplicates, to_check = [], [], []
    for i, msg in enumerate(messages):
        coords = find_coordinates(msg["text"])
        if not coords:
            short = SHORT_LINK.search(msg["text"])
            if short:
                to_check.append(f"{msg['time']:%d.%m.%Y}  קישור מקוצר בלי קואורדינטות: {short.group(0)}")
            continue

        lat, lng = coords
        name, extra = names[i]
        name = name or f"מקום מוואטסאפ {msg['time']:%d.%m.%Y}"
        instagram = INSTAGRAM.search(msg["text"])

        # כפילות? בודקים מול מה שכבר במסד ומול מה שכבר מצאנו עכשיו
        twin = next((n for n, la, ln in existing if distance_m(lat, lng, la, ln) < DUPLICATE_METERS), None)
        if twin:
            duplicates.append(f"{name}  ←  כבר קיים: {twin}")
            continue
        existing.append((name, lat, lng))

        new_places.append({
            "name": name,
            "type": guess_type(name),
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "description": (extra + " · " if extra else "") + f"יובא מוואטסאפ ({msg['time']:%d.%m.%Y})",
            "instagram": instagram.group(0) if instagram else "",
            "visited": "אינסטגרם",
        })

    print(f"\nנמצאו {len(new_places)} מקומות חדשים:\n")
    for p in new_places:
        print(f"  {p['type']:6}  {p['name']}")
    print(f"\nדילגתי על {len(duplicates)} מקומות שכבר קיימים:")
    for d in duplicates:
        print("  " + d)
    if to_check:
        print("\nלבדיקה ידנית:")
        for t in to_check:
            print("  " + t)

    with open(PREVIEW, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(new_places)

    print(f"\nהרשימה נשמרה בקובץ {PREVIEW}")
    print("פתחי אותו, תקני שמות וסוגים (ומחקי שורות שלא רוצים), ואז הריצי:")
    print("    python import_whatsapp.py --save")


# ---------- שלב 2: שמירה במסד הנתונים ----------
def save():
    with open(PREVIEW, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    conn = sqlite3.connect(DB_PATH)
    for row in rows:
        conn.execute("""
            INSERT INTO places (name, type, lat, lng, description, instagram, visited)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (row["name"], row["type"], float(row["lat"]), float(row["lng"]),
              row["description"], row["instagram"], row["visited"] or "אינסטגרם"))
    conn.commit()
    conn.close()
    print(f"✅ {len(rows)} מקומות נשמרו במסד הנתונים!")


if __name__ == "__main__":
    if "--save" in sys.argv:
        save()
    elif len(sys.argv) >= 2:
        preview(sys.argv[1])
    else:
        print("שימוש: python import_whatsapp.py _chat.txt   (ואחר כך: python import_whatsapp.py --save)")