import json
import sqlite3
from flask import Flask, render_template, request, send_from_directory, redirect, session, url_for
import os
import datetime
from werkzeug.utils import secure_filename



app = Flask(__name__, static_folder='templates')
app.secret_key = 'your_secret_key'  # обязательно для сессий

UPLOAD_FOLDER = os.path.join('static', 'uploads')  # Папка для хранения файлов

WEB_PATH_PREFIX = 'uploads'  # Для HTML-ссылки

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'jpg', 'png', 'jpeg', 'gif'}  # Разрешённые типы файлов

# Создаём папку uploads, если её нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# Обслуживаем статические файлы из папки 'main'
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(app.static_folder), path)

@app.route('/')
def index():
    return render_template('login.html')  # покажет login.html при заходе

# Функции для работы с базой данных
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Маршрут для входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()

    if user:
        session['user_id'] = user['id']
        session['role'] = user['role']
        if user['role'] == 'teacher':
            return redirect(url_for('teacher_dashboard'))  # Переход на страницу учителя
        else:
            return redirect(url_for('student_dashboard'))  # Переход на страницу ученика
    else:
        return '❌ Неверный логин или пароль'

# Маршрут для регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
        conn.commit()

        return redirect('/login')  # Перенаправить на страницу входа после успешной регистрации
    return render_template('register.html')  # Страница регистрации

# Маршрут для выхода
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Удалить user_id из сессии
    session.pop('role', None)  # Удалить роль из сессии
    return redirect('/')  # Перенаправить на страницу входа

@app.route('/teacher')
def teacher_dashboard():
    # Получаем текущую дату
    current_date = datetime.datetime.now()
    year = current_date.year
    month = current_date.month

    # Подключаемся к базе данных
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Настроим курсор для возвращения строк как словарей
    cursor = conn.cursor()

    # Получаем все даты с заданиями для текущего месяца
    cursor.execute("SELECT DISTINCT date FROM assignments WHERE strftime('%Y-%m', date) = ?", (f"{year}-{month:02d}",))
    assignment_dates = {row['date'] for row in cursor.fetchall()}  # Используем row['date'], потому что row — это словарь
    conn.close()

    # Передаём данные в шаблон
    return render_template('teacher_dashboard.html', year=year, month=month, assignment_dates=assignment_dates)



@app.route('/student')
def student_dashboard():
    # Получаем текущую дату
    current_date = datetime.datetime.now()
    year = current_date.year
    month = current_date.month

    # Получаем все даты с заданиями для текущего месяца
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # <-- вот это добавлено
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM assignments WHERE strftime('%Y-%m', date) = ?", (f"{year}-{month:02d}",))
    assignment_dates = {row['date'] for row in cursor.fetchall()}
    conn.close()

    return render_template('student_dashboard.html', year=year, month=month, assignment_dates=assignment_dates)



@app.before_request
def check_role():
    if request.path.startswith('/static/'):
        return
    if request.path in ['/login', '/register', '/']:
        return
    if 'role' not in session:
        return redirect(url_for('index'))

@app.route('/')
def calendar_view():
    return render_template('calendar.html')

@app.route('/day/<date>', methods=['GET', 'POST'])
def day_view(date):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Если учитель отправил форму
    if request.method == 'POST' and session.get('role') == 'teacher':
        content = request.form['content']
        cursor.execute('INSERT INTO assignments (date, content) VALUES (?, ?)', (date, content))
        conn.commit()

    # Получаем все задания на этот день
    cursor.execute('SELECT * FROM assignments WHERE date = ?', (date,))
    assignments = cursor.fetchall()
    conn.close()

    return render_template('day_assignments.html', date=date, assignments=assignments, role=session.get('role'))


@app.route('/delete_assignment/<int:assignment_id>/<date>', methods=['POST'])
def delete_assignment(assignment_id, date):
    if session.get('role') != 'teacher':
        return "⛔ Нет доступа", 403

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM assignments WHERE id = ?', (assignment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('day_view', date=date))

@app.route('/edit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
def edit_assignment(assignment_id):
    if session.get('role') != 'teacher':
        return "⛔ Нет доступа", 403

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        new_content = request.form['content']
        cursor.execute('UPDATE assignments SET content = ? WHERE id = ?', (new_content, assignment_id))
        conn.commit()
        cursor.execute('SELECT date FROM assignments WHERE id = ?', (assignment_id,))
        date = cursor.fetchone()['date']
        conn.close()
        return redirect(url_for('day_view', date=date))

    cursor.execute('SELECT * FROM assignments WHERE id = ?', (assignment_id,))
    assignment = cursor.fetchone()
    conn.close()

    return render_template('edit_assignment.html', assignment=assignment)

@app.route('/calendar', methods=['GET'])
def calendar():
    # Получаем текущий месяц
    current_date = datetime.datetime.now()
    year = current_date.year
    month = current_date.month

    # Получаем все даты, для которых есть задания
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM assignments WHERE strftime('%Y-%m', date) = ?", (f"{year}-{month:02d}",))
    assignment_dates = {row['date'] for row in cursor.fetchall()}
    conn.close()

    return render_template('calendar.html', year=year, month=month, assignment_dates=assignment_dates)


# Проверка расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/day/<date>', methods=['GET', 'POST'])
def day_assignments(date):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        content = request.form['content']
        file = request.files.get('assignment_file')

        # Изначально установим file_path как None
        file_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path_on_disk = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path_on_disk)

            # Устанавливаем file_path только если файл был успешно загружен
            file_path = os.path.join(WEB_PATH_PREFIX, filename)

        # Записываем задание в базу данных с file_path (может быть None)
        cursor.execute(''' 
            INSERT INTO assignments (date, content, file_path) 
            VALUES (?, ?, ?)
        ''', (date, content, file_path))
        conn.commit()

        return redirect(url_for('day_assignments', date=date))

    cursor.execute('SELECT * FROM assignments WHERE date = ?', (date,))
    assignments = cursor.fetchall()

    conn.close()

    return render_template('day_assignments.html', assignments=assignments, date=date)




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)