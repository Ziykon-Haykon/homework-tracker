import sqlite3

def check_db():

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


    user_id = 1  
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        print(f"Пользователь найден: {user}")
    else:
        print(f"Пользователь с id {user_id} не найден.")

    cursor.execute('SELECT * FROM grades WHERE student_id = ?', (user_id,))
    grades = cursor.fetchall()
    if grades:
        print(f"Оценки: {grades}")
    else:
        print(f"Нет оценок для пользователя с id {user_id}.")

    conn.close()


if __name__ == "__main__":
    check_db()

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('DROP TABLE IF EXISTS users')
cursor.execute('DROP TABLE IF EXISTS assignments')
cursor.execute('DROP TABLE IF EXISTS homework')
cursor.execute('DROP TABLE IF EXISTS grades')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('student', 'teacher')) NOT NULL,
    email TEXT UNIQUE NOT NULL  -- Добавляем почту
)
''')

# Таблица заданий
cursor.execute('''
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    content TEXT NOT NULL,
    subject TEXT NOT NULL,  -- Добавляем предмет
    file_path TEXT  -- файл, прикрепленный к заданию
)
''')


cursor.execute('''
CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    assignment_id INTEGER,  -- Ссылка на задание
    grade REAL,
    status TEXT CHECK(status IN ('done', 'pending')) NOT NULL,
    FOREIGN KEY(student_id) REFERENCES users(id),
    FOREIGN KEY(assignment_id) REFERENCES assignments(id)
)
''')

try:
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('teacher', '1234', 'teacher')")
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('student', '5678', 'student')")
except sqlite3.IntegrityError:
    print("Пользователи уже существуют")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
result = cursor.fetchone()

if result:
    print("Таблица 'users' существует.")
else:
    print("Таблица 'users' не найдена.")


conn.commit()
conn.close()

print("все ок")
print("база еть")
