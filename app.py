from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import json
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'obe-portal-secret-key-2024')

# ---- Production settings for Render / Railway (reverse proxy + HTTPS) ----
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
is_production = os.environ.get('RENDER') or os.environ.get('RAILWAY_ENVIRONMENT')
app.config['SESSION_COOKIE_SECURE'] = bool(is_production)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'https'

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# ---------- Database ----------

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all required tables on startup."""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, marks REAL, percentage REAL, gp REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS faculty_data (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL DEFAULT '[]'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS program_list (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL DEFAULT '[]'
        )
    """)
    conn.commit()
    conn.close()

# ---------- Auth ----------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("email") or request.form.get("username", "")
        password = request.form.get("password", "")
        if username == "admin" and password == "admin123":
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        return render_template("login.html", error="Invalid credentials. Try admin / admin123")
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- Pages (protected) ----------

@app.route("/")
@login_required
def home():
    return render_template("co_po.html")

@app.route("/student-performance")
@login_required
def student_performance():
    return render_template("student_performance.html")

@app.route("/faculty")
@login_required
def faculty():
    return render_template("faculty.html")

@app.route("/str")
@login_required
def str_page():
    return render_template("str.html")

@app.route("/str-table")
@login_required
def str_table():
    return render_template("str_table.html")

@app.route("/development")
@login_required
def development():
    return render_template("development.html")

@app.route("/six")
@login_required
def six():
    return render_template("six.html")

@app.route("/technical-support")
@login_required
def technical_support():
    return render_template("technical_support.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/co-po")
@login_required
def co_po():
    return render_template("co_po.html")


# ---------- API: Students ----------

@app.route("/save-student", methods=["POST"])
@login_required
def save_student():
    data = request.json
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO students (name, marks, percentage, gp)
        VALUES (?, ?, ?, ?)
    """, (data["name"], data["marks"], data["percentage"], data["gp"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Student data saved successfully"})

@app.route("/get-students")
@login_required
def get_students():
    conn = connect_db()
    cur = conn.cursor()
    # Table is guaranteed to exist because init_db() runs on startup
    rows = cur.execute("SELECT * FROM students").fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return jsonify(result)

# ---------- API: Faculty ----------

@app.route("/api/faculty", methods=["GET"])
@login_required
def get_faculty():
    conn = connect_db()
    cur = conn.cursor()
    row = cur.execute("SELECT data FROM faculty_data WHERE id = 1").fetchone()
    conn.close()
    return jsonify(json.loads(row['data']) if row else [])

@app.route("/api/faculty", methods=["POST"])
@login_required
def save_faculty_api():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO faculty_data (id, data) VALUES (1, ?)",
        (json.dumps(request.json),)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Faculty data saved"})

# ---------- API: Programs ----------

@app.route("/api/programs", methods=["GET"])
@login_required
def get_programs():
    conn = connect_db()
    cur = conn.cursor()
    row = cur.execute("SELECT data FROM program_list WHERE id = 1").fetchone()
    conn.close()
    return jsonify(json.loads(row['data']) if row else [])

@app.route("/api/programs", methods=["POST"])
@login_required
def save_programs():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO program_list (id, data) VALUES (1, ?)",
        (json.dumps(request.json),)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Programs saved"})


# Ensure tables exist when served by a production WSGI server (e.g., Gunicorn on Render).
init_db()

# ---------- Run ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)