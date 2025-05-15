import json
import sqlite3
from flask import Flask, render_template, request, send_from_directory, redirect, session, url_for, flash, make_response
import os
import datetime
from werkzeug.utils import secure_filename



app = Flask(__name__, static_folder='templates')
app.secret_key = 'your_secret_key'  # обязательно для сессий

# 🔧 Настройки загрузки
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'jpg', 'png', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 🧱 Убедиться, что папка существует
if not os.path.exists(UPLOAD_FOLDER):
  os.makedirs(UPLOAD_FOLDER)


# ✅ Проверка разрешений


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
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
            print(f"Сессия: {session['user_id']}")

            if user['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            return '❌ Неверный логин или пароль'

    return render_template('login.html')  # ← Это для GET





@app.route('/protected')
def protected():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Если пользователь не авторизован, перенаправляем на страницу входа
    return 'Здесь защищенная страница для авторизованных пользователей'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']  # Новое поле
        password = request.form['password']
        role = request.form['role']
        email = request.form['email']
        teacher_code = request.form.get('teacher_code', '')

        TEACHER_SECRET = 'teach2024'

        if role == 'teacher' and teacher_code != TEACHER_SECRET:
            flash("Неверный код учителя!", "danger")
            return redirect('/register')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        try:
            # Добавим поле name в запрос
            cursor.execute('''INSERT INTO users (username, name, password, role, email) 
                              VALUES (?, ?, ?, ?, ?)''', 
                              (username, name, password, role, email))
            conn.commit()
            flash("Успешная регистрация!", "success")
            print(f"Пользователь {username} ({name}) зарегистрирован!")
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Имя пользователя уже занято", "danger")
            return redirect('/register')
        except Exception as e:
            flash(f"Ошибка при регистрации: {str(e)}", "danger")
            return redirect('/register')
        finally:
            conn.close()

    return render_template('register.html')




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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')

    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    if request.method == 'POST':
        if role == 'teacher':
            content = request.form.get('content')
            subject = request.form.get('subject')  # <-- получаем subject из формы
            file = request.files.get('file')
            file_path = None

            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            title = request.form.get('title') or "Без названия"

            db.execute(
                'INSERT INTO assignments (title, date, content, file_path, subject) VALUES (?, ?, ?, ?, ?)',
                (title, date, content, file_path, subject)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('day_view', date=date))


        elif role == 'student':
            comment = request.form.get('content')
            student_file = request.files.get('student_file')
            file_path = None

            if student_file and student_file.filename:
                filename = secure_filename(student_file.filename)
                file_path = filename
                student_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            db.execute(
                'INSERT INTO submissions (assignment_id, student_id, date, comment, file_path) VALUES (?, ?, ?, ?, ?)',
                (request.form.get('assignment_id'), session['user_id'], date, comment, file_path)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('day_view', date=date))

    # --- Получаем все задания на дату ---
    db.execute('SELECT * FROM assignments WHERE date = ?', (date,))
    assignments = db.fetchall()

    # --- Определяем student_id в зависимости от роли ---
    if role == 'teacher':
        student_id = request.args.get('student_id')
    else:
        student_id = session['user_id']

    # --- Для каждого задания добавляем данные сдачи (submission) конкретного студента ---
    assignments_with_submissions = []
    for a in assignments:
        db.execute('''
            SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?
        ''', (a['id'], student_id))
        submission = db.fetchone()

        # Преобразуем Row в dict, чтобы добавить новое поле
        a_dict = dict(a)
        a_dict['submission'] = submission
        assignments_with_submissions.append(a_dict)
    

    students = []
    if role == 'teacher':
        db.execute("SELECT id, name FROM users WHERE role = 'student'")
        students = db.fetchall()

        conn.close()

    return render_template(
        'day_assignments.html',
        date=date,
        assignments=assignments_with_submissions,
        role=role,
        student_id=student_id,
        students=students  # <--- передаём список студентов
    )








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
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        new_content = request.form.get('content')
        cursor.execute('UPDATE assignments SET content = ? WHERE id = ?', (new_content, assignment_id))
        conn.commit()
        conn.close()
        return redirect(url_for('day_view', date=request.args.get('date')))  # если передавал дату

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




@app.route('/user.html') 
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Защита: если не авторизован

    user_id = session['user_id']

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Получаем данные пользователя
    cursor.execute('SELECT username, role, email, class_name FROM users WHERE id = ?', (user_id,))

    user = cursor.fetchone()
    print(f"Пользователь: {user}")  # Логируем, что мы получили из базы данных

    # Получаем оценки и задания
    cursor.execute('''
        SELECT subject, AVG(grade) as average_grade,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed
        FROM grades
        WHERE student_id = ?
        GROUP BY subject
    ''', (user_id,))
    grades = cursor.fetchall()
    print(f"Оценки: {grades}")  # Логируем, что мы получили из базы данных

    conn.close()

    # Отключаем кеширование для страницы
    response = make_response(render_template('user.html', user=user, grades=grades))
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    response.cache_control.must_revalidate = True

    return response


@app.route('/grade/<int:assignment_id>/<int:student_id>', methods=['POST'])
def grade_assignment(assignment_id, student_id):
    grade = request.form.get('grade')
    status = request.form.get('status')
    date = request.form.get('date')  # <-- ВАЖНО: теперь date из формы!

    conn = get_db_connection()
    existing_grade = conn.execute(
        'SELECT * FROM grades WHERE student_id = ? AND assignment_id = ?',
        (student_id, assignment_id)
    ).fetchone()

    if existing_grade:
        conn.execute(
            'UPDATE grades SET grade = ?, status = ? WHERE student_id = ? AND assignment_id = ?',
            (grade, status, student_id, assignment_id)
        )
    else:
        conn.execute(
            'INSERT INTO grades (student_id, assignment_id, grade, status, subject) VALUES (?, ?, ?, ?, ?)',
            (student_id, assignment_id, grade, status, 'your_subject')
        )

    conn.commit()
    conn.close()

    return redirect(url_for('day_view', date=date))  # <-- Теперь всё будет работать!







@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



if __name__ == '__main__':
    
    

    app.run(debug=True, host='0.0.0.0', port=3000)