import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Удаляем существующие таблицы (если нужно пересоздать)
cursor.execute('DROP TABLE IF EXISTS users')
cursor.execute('DROP TABLE IF EXISTS assignments')
cursor.execute('DROP TABLE IF EXISTS homework')

# Создаем таблицу пользователей (обновленная версия)
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('student', 'teacher')) NOT NULL
)
''')

# Создаем таблицу заданий (унифицированная версия)
cursor.execute('''
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,  -- Формат: YYYY-MM-DD
    subject TEXT NOT NULL,
    task_text TEXT NOT NULL,
    teacher_id INTEGER NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES users(id)
)
''')

# Добавляем тестовых пользователей
try:
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('teacher', '1234', 'teacher')")
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('student', '5678', 'student')")
except sqlite3.IntegrityError:
    print("Пользователи уже существуют")

conn.commit()
conn.close()

print("✅ База данных успешно создана!")
print("Тестовые пользователи добавлены в базу данных!")