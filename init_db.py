import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Таблица пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('student', 'teacher')) NOT NULL
)
''')

# Таблица домашних заданий
cursor.execute('''
CREATE TABLE IF NOT EXISTS homework (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    subject TEXT NOT NULL,
    content TEXT NOT NULL
)
''')

cursor.execute ('''
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    subject TEXT NOT NULL,
    assignment_text TEXT NOT NULL,
    created_by INTEGER NOT NULL,  -- Ссылка на учителя
    FOREIGN KEY (created_by) REFERENCES users(id)
)
''')

cursor.execute("INSERT INTO users (username, password, role) VALUES ('teacher', '1234', 'teacher')")
cursor.execute("INSERT INTO users (username, password, role) VALUES ('student', '5678', 'student')")

conn.commit()
conn.close()

print("✅ База данных успешно создана!")
print("Тестовые пользователи добавлены в базу данных!")
