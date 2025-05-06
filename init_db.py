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


cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL  -- "student" или "teacher"
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    content TEXT NOT NULL
)
''')

# Добавляем новый столбец, если его ещё нет
cursor.execute('''
ALTER TABLE assignments ADD COLUMN file_path TEXT;
''')



# Проверяем, существует ли столбец file_path
cursor.execute("PRAGMA table_info(assignments);")
columns = [column[1] for column in cursor.fetchall()]
if 'file_path' not in columns:
    cursor.execute('''
    ALTER TABLE assignments ADD COLUMN file_path TEXT;
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