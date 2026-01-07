from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from markupsafe import Markup, escape
import os, uuid, sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "resume-ai-secret"

# Upload config
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = "resume.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

# ---------------- BUILD RESUME ----------------
@app.route('/openai', methods=['GET', 'POST'])
def openai():
    if request.method == 'POST':
        profile_image_url = None

        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_name)
                file.save(file_path)
                profile_image_url = url_for('static', filename=f'uploads/{unique_name}')

        form = request.form
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO resumes
            (name, headline, email, phone, location, linkedin, website, summary, profile_image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            form.get('name'),
            form.get('headline'),
            form.get('email'),
            form.get('phone'),
            form.get('location'),
            form.get('linkedin'),
            form.get('website'),
            form.get('summary'),
            profile_image_url
        ))

        resume_id = cur.lastrowid

        if form.get('skills'):
            for skill in form.get('skills').split(','):
                cur.execute("INSERT INTO skills (resume_id, skill) VALUES (?, ?)", (resume_id, skill.strip()))

        if form.get('education'):
            cur.execute("INSERT INTO education (resume_id, description) VALUES (?, ?)", (resume_id, form.get('education')))

        if form.get('experience'):
            cur.execute("INSERT INTO experiences (resume_id, description) VALUES (?, ?)", (resume_id, form.get('experience')))

        if form.get('certifications'):
            cur.execute("INSERT INTO certifications (resume_id, title) VALUES (?, ?)", (resume_id, form.get('certifications')))

        if form.get('activities'):
            cur.execute("INSERT INTO activities (resume_id, activity) VALUES (?, ?)", (resume_id, form.get('activities')))

        conn.commit()
        conn.close()

        return redirect(url_for('list_resumes'))

    return render_template('openAI.html')

# ---------------- LIST RESUMES ----------------
@app.route('/resumes')
def list_resumes():
    conn = get_db()
    resumes = conn.execute("SELECT * FROM resumes ORDER BY id DESC").fetchall()

    for r in resumes:
        r = dict(r)
    conn.close()

    return render_template('resume_list.html', resumes=resumes)

# ---------------- VIEW RESUME ----------------
@app.route('/resume/<int:resume_id>')
def view_resume(resume_id):
    conn = get_db()
    cur = conn.cursor()

    resume_row = cur.execute(
        "SELECT * FROM resumes WHERE id = ?", (resume_id,)
    ).fetchone()

    if not resume_row:
        abort(404)

    # Convert main resume row to dict
    resume = dict(resume_row)

    # Skills
    skills_rows = cur.execute(
        "SELECT skill FROM skills WHERE resume_id = ?", (resume_id,)
    ).fetchall()
    resume['skills'] = ', '.join([row['skill'] for row in skills_rows])

    # Education
    edu_row = cur.execute(
        "SELECT description FROM education WHERE resume_id = ?", (resume_id,)
    ).fetchone()
    resume['education'] = edu_row['description'] if edu_row else ''

    # Experience
    exp_row = cur.execute(
        "SELECT description FROM experiences WHERE resume_id = ?", (resume_id,)
    ).fetchone()
    resume['experience'] = exp_row['description'] if exp_row else ''

    # Certifications
    cert_row = cur.execute(
        "SELECT title FROM certifications WHERE resume_id = ?", (resume_id,)
    ).fetchone()
    resume['certifications'] = cert_row['title'] if cert_row else ''

    # Activities
    act_row = cur.execute(
        "SELECT activity FROM activities WHERE resume_id = ?", (resume_id,)
    ).fetchone()
    resume['activities'] = act_row['activity'] if act_row else ''

    conn.close()
    return render_template('resume.html', **resume)


# ---------------- DELETE RESUME ----------------
@app.route('/resume/delete/<int:resume_id>', methods=['POST'])
def delete_resume(resume_id):
    conn = get_db()
    conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------------- FILTER ----------------
@app.template_filter('nl2br')
def nl2br(s):
    return Markup(escape(s).replace('\n', '<br>')) if s else ''

if __name__ == '__main__':
    app.run(debug=True)
