import json
import sqlite3
from flask import Flask, render_template, request, send_from_directory, redirect, session, url_for
import os

app = Flask(__name__, static_folder='templates')
app.secret_key = 'your_secret_key'  # обязательно для сессий

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
    return render_template('teacher_dashboard.html')  # Страница учителя

@app.route('/student')
def student_dashboard():
    return render_template('student_dashboard.html')  # Страница ученика

@app.route('/date/<date>', methods=['GET'])
def view_day_assignments(date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM assignments WHERE date = ?', (date,))
    assignments = cursor.fetchall()
    conn.close()
    return render_template('day_assignments.html', assignments=assignments, date=date)

@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    if request.method == 'POST':
        date = request.form['date']
        subject = request.form['subject']
        assignment_text = request.form['assignment_text']
        created_by = session.get('user_id')  # Учитель, который добавляет задание
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO assignments (date, subject, assignment_text, created_by) VALUES (?, ?, ?, ?)', 
                       (date, subject, assignment_text, created_by))
        conn.commit()
        conn.close()
        return redirect(f'/date/{date}')  # Перенаправление на страницу с заданиями на этот день

@app.before_request
def check_role():
    if request.path.startswith('/static/'):
        return
    if request.path in ['/login', '/register', '/']:
        return
    if 'role' not in session:
        return redirect(url_for('index'))
    
# Загрузка всех заданий
def load_homework():
    with open('homework.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def calendar_view():
    return render_template('calendar.html')

@app.route('/day/<date>', methods=['GET'])
def show_day(date):
    try:
        # Предположим, homework.json содержит задания на каждый день в формате { "YYYY-MM-DD": [...] }
        homework_data = load_homework()  # Загружаем все задания
        tasks = homework_data.get(date, [])  # Получаем задания на выбранную дату или пустой список
        return render_template('day_assignments.html', date=date, tasks=tasks)
    except Exception as e:
        print(f"Error: {e}")
        return f"Ошибка при загрузке заданий для {date}", 500
    

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        date = request.form['date']
        subject = request.form['subject']
        task_text = request.form['task_text']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO assignments (date, subject, task_text, teacher_id)
            VALUES (?, ?, ?, ?)
        ''', (date, subject, task_text, session['user_id']))
        conn.commit()
        conn.close()
        
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('add_task.html')

@app.route('/view_tasks')
def view_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if session.get('role') == 'teacher':
        cursor.execute('''
            SELECT * FROM assignments 
            WHERE teacher_id = ?
            ORDER BY date DESC
        ''', (session['user_id'],))
    else:
        cursor.execute('''
            SELECT a.*, u.username 
            FROM assignments a
            JOIN users u ON a.teacher_id = u.id
            ORDER BY date DESC
        ''')
    
    tasks = cursor.fetchall()
    conn.close()
    
    return render_template('view_tasks.html', tasks=tasks)




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
