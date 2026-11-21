# Campus Pathways — Student Placement Module

An alternative, beginner-friendly student placement project using Flask, Python, SQLite SQL, HTML, and CSS. It follows the student-module requirements but has its own layout, page flow, and combined student/admin login.

## Folder structure

```text
student_placement_student_module/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── dashboard.html
│   ├── admin.html
│   ├── jobs.html
│   ├── job_detail.html
│   └── applications.html
└── uploads/                 created automatically
```

## Run on Windows

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The app creates `placement.db` and two sample jobs automatically.

Demo placement admin: `admin@college.com` / `Admin@123`. Students register first; an admin approves or rejects their registration before they can sign in. For the sample Python role, add `python,sql` to profile skills and upload a resume before applying.

Included: registration, password hashing, unique email and registration number, approval/rejection, profile editing, resume upload, job browsing/details, CGPA/experience/skill eligibility checks, duplicate application prevention, application status, and a basic JSON-free browser workflow.

This is a local learning project. Set a private `SECRET_KEY` and change the demo admin password before using it beyond a classroom demo.
