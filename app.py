from flask import Flask, request, render_template, redirect, url_for, send_from_directory, abort
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads/')
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['DATABASE'] = 'incident.db'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                case_number INTEGER PRIMARY KEY AUTOINCREMENT,
                date_reported TEXT,
                date_occurred TEXT,
                type TEXT,
                location TEXT,
                description TEXT,
                severity TEXT,
                personnel_involved TEXT,
                witnesses TEXT,
                actions_taken TEXT,
                follow_up_required TEXT,
                status TEXT,
                root_cause_analysis TEXT,
                preventive_measures TEXT,
                documentation_attached TEXT,
                notes TEXT,
                documents TEXT
            )
        ''')
        conn.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        case_number = request.form.get('case_number')
        current_files = ''
        if case_number:
            with sqlite3.connect(app.config['DATABASE']) as conn:
                current_files = conn.execute(
                    'SELECT documents FROM incidents WHERE case_number = ?', (case_number,)).fetchone()[0]
                current_files = current_files if current_files else ''

        files = request.files.getlist('document')
        document_paths = current_files.split(',') if current_files else []
        file_index = len(document_paths)

        for file in files:
            if file and allowed_file(file.filename):
                file_index += 1
                filename = f"{case_number}_{file_index}{os.path.splitext(file.filename)[1]}"
                filename = secure_filename(filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                document_paths.append(filename)

        document_paths_str = ','.join(document_paths)

        with sqlite3.connect(app.config['DATABASE']) as conn:
            if case_number:  # Existing case
                conn.execute('''
                    UPDATE incidents SET
                    date_reported=?, date_occurred=?, type=?, location=?,
                    description=?, severity=?, personnel_involved=?, witnesses=?,
                    actions_taken=?, follow_up_required=?, status=?, root_cause_analysis=?,
                    preventive_measures=?, documentation_attached=?, notes=?, documents=?
                    WHERE case_number=?
                ''', (
                    request.form.get('date_reported'), request.form.get('date_occurred'), request.form.get('type'),
                    request.form.get('location'), request.form.get('description'), request.form.get('severity'),
                    request.form.get('personnel_involved'), request.form.get('witnesses'), request.form.get('actions_taken'),
                    request.form.get('follow_up_required'), request.form.get('status'), request.form.get('root_cause_analysis'),
                    request.form.get('preventive_measures'), request.form.get('documentation_attached'), request.form.get('notes'),
                    document_paths_str, case_number
                ))
            else:  # New case
                conn.execute('''
                    INSERT INTO incidents (date_reported, date_occurred, type, location, description, severity,
                    personnel_involved, witnesses, actions_taken, follow_up_required, status, root_cause_analysis,
                    preventive_measures, documentation_attached, notes, documents)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    request.form.get('date_reported'), request.form.get('date_occurred'), request.form.get('type'),
                    request.form.get('location'), request.form.get('description'), request.form.get('severity'),
                    request.form.get('personnel_involved'), request.form.get('witnesses'), request.form.get('actions_taken'),
                    request.form.get('follow_up_required'), request.form.get('status'), request.form.get('root_cause_analysis'),
                    request.form.get('preventive_measures'), request.form.get('documentation_attached'), request.form.get('notes'),
                    document_paths_str
                ))
                case_number = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.commit()

    incidents = []
    with sqlite3.connect(app.config['DATABASE']) as conn:
        incidents = conn.execute('SELECT * FROM incidents ORDER BY case_number DESC').fetchall()

    return render_template('index.html', incidents=incidents)

@app.route('/edit/<int:case_number>')
def edit_incident(case_number):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        incident = conn.execute('SELECT * FROM incidents WHERE case_number = ?', (case_number,)).fetchone()
    if incident:
        return render_template('index.html', case_to_edit=incident)
    return redirect(url_for('index'))

@app.route('/delete/<int:case_number>', methods=['POST'])
def delete_case(case_number):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('DELETE FROM incidents WHERE case_number = ?', (case_number,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/documents/<filename>')
def download_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    init_db()
    app.run(debug=True)
