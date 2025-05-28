import json
import sqlite3
from flask import Flask, render_template, request, send_from_directory, redirect, session, url_for, flash, make_response, send_file, get_flashed_messages
import os
import calendar
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import uuid


app = Flask(__name__, static_folder='templates')
app.secret_key = 'your_secret_key'  


UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'jpg', 'png', 'jpeg', 'gif',
    'doc', 'docx',                                    
    'ppt', 'pptx',                                    
    'xls', 'xlsx',                                    
    'odt', 'ods', 'odp',                             
    'zip', 'rar'                                    
}


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


if not os.path.exists(UPLOAD_FOLDER):
  os.makedirs(UPLOAD_FOLDER)





def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(app.static_folder), path)

@app.route('/')
def index():
    return render_template('login.html')  


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

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):    
            session['user_id'] = user['id']
            session['role'] = user['role']
            print(f"Сессия: {session['user_id']}")

            if user['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash("❌ Неверный логин или пароль", "danger")
            return redirect('/login')

    return render_template('login.html')  





@app.route('/protected')
def protected():
    if 'user_id' not in session:
        return redirect(url_for('login'))  
    return 'Здесь защищенная страница для авторизованных пользователей'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        get_flashed_messages()
        return render_template('register.html')

    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name'] 
        password = request.form['password']
        role = request.form['role']
        email = request.form['email']
        teacher_code = request.form.get('teacher_code', '')
        class_name = request.form.get('class_name') if role == 'student' else None
        hashed_password = generate_password_hash(password)

        TEACHER_SECRET = 'teach2024'
        if role == 'teacher' and teacher_code != TEACHER_SECRET:    
            flash("Неверный код учителя!", "danger")
            return redirect('/register')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO users (username, name, class_name, password, role, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, name, class_name, hashed_password, role, email))

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






@app.route('/logout')
def logout():
    session.pop('user_id', None)  
    session.pop('role', None)  
    return redirect('/') 

@app.route('/teacher')
def teacher_dashboard():

    current_date = datetime.now()
    year = current_date.year
    month = current_date.month


    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT date FROM assignments WHERE strftime('%Y-%m', date) = ?", (f"{year}-{month:02d}",))
    assignment_dates = {row['date'] for row in cursor.fetchall()}  
    conn.close()
    return render_template('teacher_dashboard.html', year=year, month=month, assignment_dates=assignment_dates, assignment_status_by_date={})





@app.route('/student')
def student_dashboard():
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    user_id = session.get('user_id')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Получаем ВСЕ задания за месяц
    cursor.execute("""
        SELECT id, date FROM assignments 
        WHERE strftime('%Y-%m', date) = ?
    """, (f"{year}-{month:02d}",))
    assignments = cursor.fetchall()

    # Получаем ВСЕ отправки ученика за месяц
    cursor.execute("""
        SELECT submissions.assignment_id, grades.grade
        FROM submissions
        LEFT JOIN grades 
            ON submissions.assignment_id = grades.assignment_id 
            AND submissions.student_id = grades.student_id
        WHERE submissions.student_id = ? AND strftime('%Y-%m', submissions.date) = ?
    """, (user_id, f"{year}-{month:02d}"))
    submissions = cursor.fetchall()


    # Преобразуем отправки в словарь: assignment_id → grade
    submission_grades = {row['assignment_id']: row['grade'] for row in submissions}
    assignment_status_by_date = {}  
    # Теперь по каждой дате решаем статус
    for row in assignments:
        aid = row['id']
        date = row['date']
        grade = submission_grades.get(aid)

        if grade is not None:
            new_status = 'completed'
        elif aid in submission_grades:
            new_status = 'pending'
        else:
            new_status = 'not_completed'

        print(f"{date} - assignment {aid}: grade={grade}, status={new_status}")

        current_status = assignment_status_by_date.get(date)
        priority = {'completed': 3, 'pending': 2, 'not_completed': 1}
        if not current_status or priority[new_status] > priority.get(current_status, 0):
            assignment_status_by_date[date] = new_status

    print("Final status by date:", assignment_status_by_date)

    # Календарь
    cal = calendar.Calendar()
    calendar_weeks = list(cal.itermonthdates(year, month))
    weeks = [calendar_weeks[i:i+7] for i in range(0, len(calendar_weeks), 7)]

    conn.close()

    return render_template(
        'student_dashboard.html',
        year=year,
        month=month,
        assignment_status_by_date=assignment_status_by_date,
        calendar_weeks=weeks
    )




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
            subject = request.form.get('subject')  
            file = request.files.get('file')
            file_path = None

            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            title = request.form.get('title') or "Без названия"

            db.execute(
                'INSERT INTO assignments (title, date, content, file_path, subject, teacher_id) VALUES (?, ?, ?, ?, ?, ?)',
                (title, date, content, file_path, subject, session['user_id']) 
            )
            conn.commit()
            conn.close()
            return redirect(url_for('day_view', date=date))


        elif role == 'student':
            comment = request.form.get('content')
            student_file = request.files.get('student_file')
            file_path = None

            if student_file and student_file.filename:
                filename = str(uuid.uuid4()) + "_" + secure_filename(student_file.filename)
                file_path = filename
                student_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            db.execute(
                'INSERT INTO submissions (assignment_id, student_id, date, comment, file_path) VALUES (?, ?, ?, ?, ?)',
                (request.form.get('assignment_id'), session['user_id'], date, comment, file_path)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('day_view', date=date))


    db.execute('SELECT * FROM assignments WHERE date = ?', (date,))
    assignments = db.fetchall()

 
    if role == 'teacher':
        student_id = request.args.get('student_id')
    else:
        student_id = session['user_id']

    assignments_with_submissions = []
    for a in assignments:
        db.execute('''
            SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?
        ''', (a['id'], student_id))
        submission = db.fetchone()


        if submission:
            db.execute('''
                SELECT grade FROM grades WHERE assignment_id = ? AND student_id = ?
            ''', (a['id'], student_id))
            grade = db.fetchone()
            submission = dict(submission)
            submission['grade'] = grade['grade'] if grade else None

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
        students=students  
    )


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


@app.route('/delete_assignment/<int:assignment_id>', methods=['POST'])
def delete_assignment(assignment_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM assignments WHERE id = ?', (assignment_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('teacher_dashboard'))






@app.route('/user.html', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT username, name, role, email, class_name FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    role = user['role']

    # 📊 Для учителя: обзор
    if role == 'teacher':
        cursor.execute('SELECT subject, COUNT(*) as count FROM assignments WHERE teacher_id = ? GROUP BY subject', (user_id,))
        subject_overview = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) FROM assignments WHERE teacher_id = ?', (user_id,))
        total_assignments = cursor.fetchone()[0]

        cursor.execute('''SELECT COUNT(*) FROM submissions 
                          JOIN assignments ON submissions.assignment_id = assignments.id
                          WHERE assignments.teacher_id = ?''', (user_id,))
        total_submissions = cursor.fetchone()[0]

        cursor.execute('''SELECT COUNT(*) FROM grades 
                          JOIN assignments ON grades.assignment_id = assignments.id
                          WHERE assignments.teacher_id = ?''', (user_id,))
        graded = cursor.fetchone()[0]
    else:
        subject_overview = []
        total_assignments = 0
        total_submissions = 0
        graded = 0

    # 📥 Приём ответа на задание
    if request.method == 'POST' and role == 'student':
        comment = request.form.get('content')
        assignment_id = request.form.get('assignment_id')
        student_file = request.files.get('student_file')
        file_path = None

        if student_file and student_file.filename:
            filename = secure_filename(student_file.filename)
            file_path = filename
            student_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor.execute('''
            INSERT INTO submissions (assignment_id, student_id, date, comment, file_path)
            VALUES (?, ?, date('now'), ?, ?)
        ''', (assignment_id, user_id, comment, file_path))
        conn.commit()

    # 📚 Общие данные по предметам
    cursor.execute('SELECT DISTINCT subject FROM assignments')
    subjects = cursor.fetchall()
    subject_stats = []

    for subject_row in subjects:
        subject = subject_row['subject']
        cursor.execute('SELECT * FROM assignments WHERE subject = ?', (subject,))
        assignments = cursor.fetchall()

        detailed_assignments = []
        grades_list = []

        for a in assignments:
            if role == 'student':
                cursor.execute('''
                    SELECT grade, status FROM grades
                    WHERE student_id = ? AND assignment_id = ?
                ''', (user_id, a['id']))
                grade_row = cursor.fetchone()

                if not grade_row:
                    cursor.execute('''
                        SELECT * FROM submissions
                        WHERE student_id = ? AND assignment_id = ?
                    ''', (user_id, a['id']))
                    submission = cursor.fetchone()
                else:
                    submission = None

                detailed_assignments.append({
                    'id': a['id'],
                    'content': a['content'],
                    'file_path': a['file_path'],
                    'grade': grade_row['grade'] if grade_row else None,
                    'status': grade_row['status'] if grade_row else 'not_submitted',
                    'submitted': bool(submission)
                })

                if grade_row and grade_row['grade'] is not None:
                    grades_list.append(grade_row['grade'])
            else:
                detailed_assignments.append({
                    'id': a['id'],
                    'content': a['content'],
                    'file_path': a['file_path'],
                    'grade': None,
                    'status': 'not_applicable',
                    'submitted': False
                })

        avg_grade = sum(grades_list) / len(grades_list) if grades_list else 0
        completed = sum(1 for a in detailed_assignments if a['status'] == 'done')

        subject_stats.append({
            'subject': subject,
            'average_grade': avg_grade,
            'completed': completed,
            'total': len(detailed_assignments),
            'assignments': detailed_assignments
        })

    conn.close()

    # 🎨 Передаём всё в шаблон
    response = make_response(render_template(
        'user.html',
        user=user,
        grades=subject_stats,
        subject_overview=subject_overview if role == 'teacher' else None,
        total_assignments=total_assignments if role == 'teacher' else None,
        total_submissions=total_submissions if role == 'teacher' else None,
        graded=graded if role == 'teacher' else None
    ))
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    response.cache_control.must_revalidate = True

    return response





@app.route('/grade/<int:assignment_id>/<int:student_id>', methods=['POST'])
def grade_assignment(assignment_id, student_id):
    grade = request.form.get('grade')
    status = request.form.get('status')
    date = request.form.get('date') 

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

    return redirect(url_for('day_view', date=date))  









@app.route('/uploads/<filename>')
def uploaded_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)



if __name__ == '__main__':
    
    

    app.run(debug=True, host='0.0.0.0', port=3000)