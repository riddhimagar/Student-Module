import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
DB = "placement.db"
Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True)


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL, last_name TEXT NOT NULL, dob TEXT,
            location TEXT, education TEXT, experience INTEGER DEFAULT 0,
            skills TEXT, hobbies TEXT, interests TEXT, positions TEXT,
            job_location TEXT, email TEXT UNIQUE NOT NULL, phone TEXT,
            password TEXT NOT NULL, resume TEXT, approved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL,
            title TEXT NOT NULL, location TEXT, package TEXT, vacancy INTEGER DEFAULT 1,
            min_cgpa REAL DEFAULT 0, min_experience INTEGER DEFAULT 0,
            required_skills TEXT, description TEXT
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            job_id INTEGER NOT NULL REFERENCES jobs(id),
            experience INTEGER DEFAULT 0, relocate TEXT, worked_on TEXT,
            status TEXT DEFAULT 'Applied', applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, job_id)
        );
        """)
        if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
            db.executemany("""INSERT INTO jobs
                (company,title,location,package,vacancy,min_cgpa,min_experience,required_skills,description)
                VALUES (?,?,?,?,?,?,?,?,?)""", [
                ("Bright Tech", "Python Developer", "Bengaluru", "6 LPA", 3, 6.0, 0, "python,sql", "Build and maintain web applications."),
                ("Northstar Systems", "Junior Web Developer", "Pune", "5 LPA", 2, 5.5, 0, "html,css", "Work with a team building web products.")
            ])
        # Demo placement-cell account: admin@college.com / Admin@123
        if not db.execute("SELECT id FROM students WHERE email=?", ("admin@college.com",)).fetchone():
            db.execute("""INSERT INTO students (reg_no,first_name,last_name,email,password,approved)
                VALUES (?,?,?,?,?,1)""", ("ADMIN", "Placement", "Admin", "admin@college.com", generate_password_hash("Admin@123")))


def login_required(role=None):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("This page is for placement administrators.")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return decorate


@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        if f["password"] != f["confirm_password"]:
            flash("Passwords do not match.")
            return render_template("register.html")
        try:
            with connect() as db:
                db.execute("""INSERT INTO students
                    (reg_no,first_name,last_name,dob,location,education,experience,skills,hobbies,interests,
                    positions,job_location,email,phone,password)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f["reg_no"],f["first_name"],f["last_name"],f["dob"],f["location"],f["education"],
                     f.get("experience",0),f["skills"],f["hobbies"],f["interests"],f["positions"],
                     f["job_location"],f["email"].lower(),f["phone"],generate_password_hash(f["password"])))
            flash("Registration submitted. Sign in after the placement cell approves it.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with connect() as db:
            user = db.execute("SELECT * FROM students WHERE email=?", (request.form["email"].lower(),)).fetchone()
        if user and check_password_hash(user["password"], request.form["password"]):
            if not user["approved"]:
                flash("Your account is waiting for placement-cell approval.")
                return render_template("login.html")
            session["user_id"] = user["id"]
            session["role"] = "admin" if user["email"] == "admin@college.com" else "student"
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required()
def dashboard():
    with connect() as db:
        user = db.execute("SELECT * FROM students WHERE id=?", (session["user_id"],)).fetchone()
        if session["role"] == "admin":
            pending = db.execute("SELECT * FROM students WHERE approved=0 ORDER BY id DESC").fetchall()
            return render_template("admin.html", user=user, pending=pending)
        job_count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        app_count = db.execute("SELECT COUNT(*) FROM applications WHERE student_id=?", (user["id"],)).fetchone()[0]
    filled = sum(bool(user[k]) for k in ("phone", "location", "education", "skills", "resume"))
    completion = filled * 20
    return render_template("dashboard.html", user=user, job_count=job_count,
                           app_count=app_count, completion=completion)


@app.route("/student/<int:student_id>/<action>", methods=["POST"])
@login_required("admin")
def student_decision(student_id, action):
    if action not in ("approve", "reject"):
        return redirect(url_for("dashboard"))
    with connect() as db:
        if action == "approve":
            db.execute("UPDATE students SET approved=1 WHERE id=?", (student_id,))
        else:
            db.execute("DELETE FROM students WHERE id=? AND approved=0", (student_id,))
    flash("Student " + ("approved." if action == "approve" else "registration rejected."))
    return redirect(url_for("dashboard"))


@app.route("/jobs")
@login_required("student")
def jobs():
    with connect() as db:
        items = db.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
        applied = {row[0] for row in db.execute(
            "SELECT job_id FROM applications WHERE student_id=?", (session["user_id"],)
        ).fetchall()}
    return render_template("jobs.html", jobs=items, applied=applied)


@app.route("/jobs/<int:job_id>")
@login_required("student")
def job_detail(job_id):
    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        already_applied = db.execute(
            "SELECT id FROM applications WHERE student_id=? AND job_id=?",
            (session["user_id"], job_id)
        ).fetchone()
    if not job:
        flash("Job not found.")
        return redirect(url_for("jobs"))
    return render_template("job_detail.html", job=job, already_applied=already_applied)


@app.route("/applications")
@login_required("student")
def applications():
    with connect() as db:
        items = db.execute("""SELECT a.*,j.title,j.company,j.location,j.package
            FROM applications a JOIN jobs j ON j.id=a.job_id
            WHERE a.student_id=? ORDER BY a.id DESC""", (session["user_id"],)).fetchall()
    return render_template("applications.html", applications=items)


@app.route("/profile", methods=["GET", "POST"])
@login_required("student")
def profile():
    with connect() as db:
        user = db.execute("SELECT * FROM students WHERE id=?", (session["user_id"],)).fetchone()
        if request.method == "POST":
            f = request.form
            resume = user["resume"]
            file = request.files.get("resume")
            if file and file.filename:
                if Path(file.filename).suffix.lower() not in (".pdf", ".doc", ".docx"):
                    flash("Resume must be PDF, DOC, or DOCX.")
                    return render_template("profile.html", user=user)
                resume = secure_filename(f"{user['id']}_{file.filename}")
                file.save(Path(app.config["UPLOAD_FOLDER"]) / resume)
            db.execute("""UPDATE students SET phone=?,location=?,education=?,experience=?,skills=?,hobbies=?,
                interests=?,positions=?,job_location=?,resume=? WHERE id=?""",
                (f["phone"],f["location"],f["education"],f.get("experience",0),f["skills"],f["hobbies"],
                 f["interests"],f["positions"],f["job_location"],resume,user["id"]))
            flash("Profile saved.")
            return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.route("/apply/<int:job_id>", methods=["POST"])
@login_required("student")
def apply(job_id):
    with connect() as db:
        student = db.execute("SELECT * FROM students WHERE id=?", (session["user_id"],)).fetchone()
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            flash("Job not found.")
            return redirect(url_for("dashboard"))
        skills = {x.strip().lower() for x in (student["skills"] or "").split(",") if x.strip()}
        needed = {x.strip().lower() for x in (job["required_skills"] or "").split(",") if x.strip()}
        if not student["resume"]:
            flash("Upload a resume in your profile before applying.")
        elif float(request.form.get("cgpa", 0) or 0) < job["min_cgpa"]:
            flash("You do not meet the minimum CGPA for this job.")
        elif int(request.form.get("experience", 0) or 0) < job["min_experience"]:
            flash("You do not meet the minimum experience for this job.")
        elif not needed.issubset(skills):
            flash("Your profile is missing one or more required skills.")
        else:
            try:
                db.execute("""INSERT INTO applications (student_id,job_id,experience,relocate,worked_on)
                    VALUES (?,?,?,?,?)""", (student["id"],job_id,request.form.get("experience",0),
                                             request.form.get("relocate"),request.form.get("worked_on")))
                flash("Application submitted.")
            except sqlite3.IntegrityError:
                flash("You have already applied for this job.")
    return redirect(url_for("job_detail", job_id=job_id))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
