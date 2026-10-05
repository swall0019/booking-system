import sqlite3
import os
import json
from datetime import datetime

DB_NAME = "bookings.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            equipment TEXT,
            department TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            purpose TEXT,
            recurrence TEXT DEFAULT 'none',
            series_id TEXT DEFAULT '',
            attachment TEXT DEFAULT '',
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Миграции для старых БД
    _migrate(cur)

    # Пользователи по умолчанию
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("admin", "admin", "admin"))
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("manager", "manager", "manager"))
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("user", "user", "user"))

    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] == 0:
        rooms = [
            ("Переговорная А", 6, "Проектор, доска", "IT"),
            ("Переговорная Б", 10, "TV, видеоконференция", "Sales"),
            ("Конференц-зал", 30, "Проектор, звук, микрофоны", "Общий"),
            ("Мини-комната", 4, "Доска", "HR"),
        ]
        cur.executemany("INSERT INTO rooms (name, capacity, equipment, department) VALUES (?, ?, ?, ?)", rooms)

    conn.commit()
    conn.close()


def _migrate(cur):
    """Добавляет недостающие колонки в старые БД."""
    cur.execute("PRAGMA table_info(rooms)")
    cols = [r[1] for r in cur.fetchall()]
    if "department" not in cols:
        cur.execute("ALTER TABLE rooms ADD COLUMN department TEXT DEFAULT ''")

    cur.execute("PRAGMA table_info(bookings)")
    cols = [r[1] for r in cur.fetchall()]
    if "recurrence" not in cols:
        cur.execute("ALTER TABLE bookings ADD COLUMN recurrence TEXT DEFAULT 'none'")
    if "series_id" not in cols:
        cur.execute("ALTER TABLE bookings ADD COLUMN series_id TEXT DEFAULT ''")
    if "attachment" not in cols:
        cur.execute("ALTER TABLE bookings ADD COLUMN attachment TEXT DEFAULT ''")


# ---------- Пользователи ----------
def check_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE username=? AND password=?",
                (username, password))
    row = cur.fetchone()
    conn.close()
    return row


def register_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')",
                    (username, password))
        conn.commit()
        return True, "Пользователь зарегистрирован"
    except sqlite3.IntegrityError:
        return False, "Пользователь с таким именем уже существует"
    finally:
        conn.close()


def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- Помещения ----------
def get_rooms():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, capacity, equipment, department FROM rooms ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_room(name, capacity, equipment, department=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO rooms (name, capacity, equipment, department) VALUES (?, ?, ?, ?)",
                (name, capacity, equipment, department))
    conn.commit()
    conn.close()


def delete_room(room_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()
    conn.close()


# ---------- Проверка занятости ----------
def is_room_free(room_id, date, time_start, time_end, exclude_id=None):
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT COUNT(*) FROM bookings
        WHERE room_id=? AND date=?
          AND NOT (time_end <= ? OR time_start >= ?)
    """
    params = [room_id, date, time_start, time_end]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    cur.execute(query, params)
    count = cur.fetchone()[0]
    conn.close()
    return count == 0


def get_busy_slots(room_id, date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.time_start, b.time_end, u.username, b.purpose, b.id
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.room_id=? AND b.date=?
        ORDER BY b.time_start
    """, (room_id, date))
    rows = cur.fetchall()
    conn.close()
    return rows


def find_free_rooms(date, time_start, time_end):
    """Возвращает список помещений, свободных в указанный интервал."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.name, r.capacity, r.equipment
        FROM rooms r
        WHERE r.id NOT IN (
            SELECT b.room_id FROM bookings b
            WHERE b.date=?
              AND NOT (b.time_end <= ? OR b.time_start >= ?)
        )
        ORDER BY r.name
    """, (date, time_start, time_end))
    rows = cur.fetchall()
    conn.close()
    return rows


def find_nearest_free(room_id, date, duration_minutes=60, from_time="08:00"):
    """Ищет ближайший свободный слот заданной длительности."""
    from datetime import datetime, timedelta

    slots = get_busy_slots(room_id, date)
    start = datetime.strptime(from_time, "%H:%M")
    end_of_day = datetime.strptime("22:00", "%H:%M")
    duration = timedelta(minutes=duration_minutes)

    while start + duration <= end_of_day:
        candidate_start = start.strftime("%H:%M")
        candidate_end = (start + duration).strftime("%H:%M")
        ok = True
        for s_start, s_end, *_ in slots:
            if not (s_end <= candidate_start or s_start >= candidate_end):
                ok = False
                # прыгнем на конец занятого слота
                start = datetime.strptime(s_end, "%H:%M")
                break
        if ok:
            return candidate_start, candidate_end
        else:
            continue
    return None, None


# ---------- Брони ----------
def add_booking(room_id, user_id, date, time_start, time_end, purpose,
                recurrence="none", series_id="", attachment="", participants=None):
    if not is_room_free(room_id, date, time_start, time_end):
        return False, "Это время уже занято"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings
            (room_id, user_id, date, time_start, time_end, purpose,
             recurrence, series_id, attachment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (room_id, user_id, date, time_start, time_end, purpose,
          recurrence, series_id, attachment))
    booking_id = cur.lastrowid

    if participants:
        for uid in participants:
            cur.execute("INSERT INTO participants (booking_id, user_id) VALUES (?, ?)",
                        (booking_id, uid))

    conn.commit()
    conn.close()
    return True, "Бронирование создано"


def update_booking(booking_id, room_id, date, time_start, time_end,
                   purpose, attachment="", participants=None):
    if not is_room_free(room_id, date, time_start, time_end, exclude_id=booking_id):
        return False, "Это время уже занято"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE bookings
        SET room_id=?, date=?, time_start=?, time_end=?, purpose=?, attachment=?
        WHERE id=?
    """, (room_id, date, time_start, time_end, purpose, attachment, booking_id))

    if participants is not None:
        cur.execute("DELETE FROM participants WHERE booking_id=?", (booking_id,))
        for uid in participants:
            cur.execute("INSERT INTO participants (booking_id, user_id) VALUES (?, ?)",
                        (booking_id, uid))

    conn.commit()
    conn.close()
    return True, "Бронирование обновлено"


def get_booking(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.room_id, b.user_id, b.date, b.time_start, b.time_end,
               b.purpose, b.recurrence, b.series_id, b.attachment, r.name, u.username
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        WHERE b.id=?
    """, (booking_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_participants(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username
        FROM participants p
        JOIN users u ON p.user_id = u.id
        WHERE p.booking_id=?
    """, (booking_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_bookings(user_id=None, is_admin=False, is_manager=False):
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT b.id, r.name, u.username, b.date, b.time_start, b.time_end,
               b.purpose, b.recurrence, b.attachment
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
    """
    params = []
    if not is_admin and not is_manager and user_id:
        query += " WHERE b.user_id=?"
        params.append(user_id)
    query += " ORDER BY b.date, b.time_start"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_bookings():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, r.name, u.username, b.date, b.time_start, b.time_end, b.purpose, b.user_id
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.id
        ORDER BY b.date DESC, b.time_start
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_booking(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()


def delete_series(series_id):
    if not series_id:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings WHERE series_id=?", (series_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rooms")
    rooms = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bookings")
    bookings = cur.fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (today,))
    today_bookings = cur.fetchone()[0]
    conn.close()
    return rooms, bookings, today_bookings


# ---------- Повторяющиеся встречи ----------
def create_recurring_bookings(room_id, user_id, date, time_start, time_end,
                              purpose, recurrence, participants=None, attachment=""):
    """
    Создаёт серию бронирований.
    recurrence: 'none' | 'daily' | 'weekly' | 'monthly'
    Создаёт 8 повторов (можно изменить).
    """
    from datetime import datetime, timedelta
    import uuid

    if recurrence == "none":
        return add_booking(room_id, user_id, date, time_start, time_end,
                           purpose, "none", "", attachment, participants)

    series_id = str(uuid.uuid4())[:8]
    start = datetime.strptime(date, "%Y-%m-%d")
    created = 0
    skipped = 0

    for i in range(8):
        if recurrence == "daily":
            cur_date = start + timedelta(days=i)
        elif recurrence == "weekly":
            cur_date = start + timedelta(weeks=i)
        elif recurrence == "monthly":
            # простое +30 дней
            cur_date = start + timedelta(days=30 * i)
        else:
            cur_date = start

        d = cur_date.strftime("%Y-%m-%d")
        ok, _ = add_booking(room_id, user_id, d, time_start, time_end,
                            purpose, recurrence, series_id, attachment, participants)
        if ok:
            created += 1
        else:
            skipped += 1

    msg = f"Создано {created} повторов"
    if skipped:
        msg += f", пропущено {skipped} (занято)"
    return True, msg


# ---------- Участники ----------
def set_participants(booking_id, user_ids):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM participants WHERE booking_id=?", (booking_id,))
    for uid in user_ids:
        cur.execute("INSERT INTO participants (booking_id, user_id) VALUES (?, ?)",
                    (booking_id, uid))
    conn.commit()
    conn.close()


# ---------- Настройки ----------
SETTINGS_FILE = "settings.json"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"theme": "light"}


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)