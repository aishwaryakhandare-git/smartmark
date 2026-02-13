from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import io
import csv
import firebase_admin
from firebase_admin import credentials, db
import time as _time
import face_recognition
from PIL import Image
from datetime import date

import firebase_admin
from firebase_admin import credentials, db
import random
import string
import time as tm
from datetime import datetime
from flask import Response 

import firebase_admin
from firebase_admin import credentials, db, auth

import cv2
import numpy as np

import base64
import uuid

from flask import Flask, render_template, request, redirect, url_for, flash, session
#import bcrypt

from flask import request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"

@app.route("/")
def index():
      # 👈 Clears any old login info
    return render_template("index.html")

# ----------------- Firebase Setup -----------------
cred = credentials.Certificate("firebase-key.json")  # Replace with your actual JSON key
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smartmarkattendance-default-rtdb.asia-southeast1.firebasedatabase.app/'
})


from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@app.route("/get_started", methods=["POST"])
def get_started():
    role = request.form.get("role")

    # ----- ADMIN -----
    if role == "admin":
        email = request.form.get("email")
        password = request.form.get("password")
        # For now, treat every admin login as valid demo login
        session["admin_email"] = email
        flash(f"Welcome Admin {email}!", "success")
        return redirect(url_for("admin_dashboard"))

    # ----- TEACHER -----
    elif role == "teacher":
        teacher_id = request.form.get("teacher_id")
        session["teacher_id"] = teacher_id
        flash(f"Welcome Teacher {teacher_id}!", "success")
        return redirect(url_for("teacher_dashboard"))

    # ----- STUDENT -----
    elif role == "student":
        student_id = request.form.get("student_id")
        session["student_id"] = student_id
        flash(f"Welcome Student {student_id}!", "success")
        return redirect(url_for("student_dashboard"))

    # fallback
    flash("Invalid role selection", "danger")
    return redirect(url_for("index"))

# ------------------ AUTHENTICATION ROUTES ------------------

@app.route("/login", methods=["POST"])
def login():
    print("🧩 FORM RECEIVED:", request.form)

    role = request.form.get("role", "").strip().lower()

    # Handle inputs separately for each role
    if role == "student":
        email = None
        student_id_input = request.form.get("student_id", "").strip()
        password = request.form.get("password", "").strip()
        print(f"🧠 Login attempt -> Student ID: {student_id_input}")
    else:
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        print(f"🧠 Login attempt -> Role: {role}, Email: {email}")

    # Skip email/password validation for teacher login
    # Validate differently for admin/student
    # VALIDATION
    if role == "admin":
        if not email or not password:
            flash("⚠️ Email and password required!", "warning")
            return redirect(url_for("index"))

    elif role == "student":
        if not request.form.get("student_id") or not password:
            flash("⚠️ Student ID and Password required!", "warning")
            return redirect(url_for("index"))

    def check_user(path):
        users = db.reference(path).get() or {}
        if not isinstance(users, dict):
            users = {}
        for uid, data in users.items():
            if data.get("email") == email:
                stored_pass = data.get("password")
                if stored_pass == password:
                    return uid, data  # ✅ return both id and data
                else:
                    flash("❌ Incorrect password!", "danger")
                    return None, None
        return None

    # 🔹 Admin login (ONLY verify, do NOT create new admin)
    if role == "admin":
        admins = db.reference("admins").get() or {}

        found_admin = None
        found_id = None

        # Search for matching email and password
        for uid, data in admins.items():
            if data.get("email") == email and data.get("password") == password:
                found_admin = data
                found_id = uid
                break

        # If no admin matched
        if not found_admin:
            flash("❌ Invalid admin email or password!", "danger")
            return redirect(url_for("index"))

        # Successful login
        session.pop("_flashes", None)
        session["role"] = "admin"
        session["logged_in"] = True
        session["admin_logged_in"] = True
        session["admin_id"] = found_id
        session["name"] = found_admin.get("name")
        session["email"] = found_admin.get("email")

        flash(f"Welcome, {found_admin.get('name', 'Admin')}!", "success")
        return redirect(url_for("admin_dashboard"))

    # 🔹 Teacher login (NAME + SUBJECT PASS)
    if role == "teacher":

        teacher_name = request.form.get("teacher_name", "").strip()
        subject_pass = request.form.get("subject_pass", "").strip()

        if not teacher_name or not subject_pass:
            flash("⚠️ Teacher name and subject password are required!", "warning")
            return redirect(url_for("index"))

        teachers = db.reference("teachers").get() or {}

        matched_uid = None
        matched_data = None

        # Find teacher by name
        for uid, data in teachers.items():
            if data.get("name", "").lower() == teacher_name.lower() and \
            data.get("subject_pass") == subject_pass:

                matched_uid = uid
                matched_data = data
                break   # <-- break ONLY after a match is found

        if not matched_uid:
            flash("❌ Invalid teacher name or subject password!", "danger")
            return redirect(url_for("index"))

        # Successful login
        session.pop("_flashes", None)
        session["role"] = "teacher"
        session["logged_in"] = True
        session["teacher_id"] = matched_uid
        session["teacher"] = matched_data
        session["name"] = matched_data.get("name")
        session["email"] = matched_data.get("email")
        session["subject_pass"] = matched_data.get("subject_pass")
        session["course"] = matched_data.get("course")
        session["class_key"] = matched_data.get("class_key")
        session["subject"] = matched_data.get("subject")
        session["admin_id"] = matched_data.get("admin_id")

        flash(f"Welcome, {matched_data.get('name', 'Teacher')}!", "success")
        return redirect(url_for("teacher_dashboard"))

    # 🔹 Student login
    if role == "student":

        # Your form uses the same fields as admin login:
        student_id_input = request.form.get("student_id", "").strip()   # <-- use the variable we created above
        student_pass_input = request.form.get("password")

        students = db.reference("students_main").get() or {}

        matched_uid = None
        matched_data = None

        # Check ID + student_pass
        for uid, data in students.items():
            if data.get("student_id") == student_id_input and data.get("student_pass") == student_pass_input:
                matched_uid = uid
                matched_data = data
                break

        if not matched_uid:
            flash("❌ Invalid Student ID or Student Password!", "danger")
            return redirect(url_for("index"))

        # Successful login
        session.pop("_flashes", None)
        session["role"] = "student"
        session["logged_in"] = True
        session["student_uid"] = matched_uid
        session["student_id"] = matched_data.get("student_id")
        session["name"] = matched_data.get("name")
        session["student_name"] = matched_data.get("name")
        session["email"] = matched_data.get("email")
        session["admin_id"] = matched_data.get("admin_id")
        session["course"] = matched_data.get("course")
        session["class_key"] = matched_data.get("class_key")

        flash(f"Welcome, {matched_data.get('name', 'Student')}!", "success")
        return redirect(url_for("student_profile"))


@app.route("/signup", methods=["POST"])
def signup():
    print("🆕 SIGNUP FORM RECEIVED:", request.form)
    print("FULL FORM DATA RECEIVED:", request.form.to_dict())

    # Collect form data
    role = request.form.get("role", "").strip().lower()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()
    institute_name = request.form.get("institute_name", "").strip()

    # Confirm password ONLY for admin
    if role == "admin":
        confirm_password = request.form.get("confirm_password", "").strip()
        if password != confirm_password:
            flash("❌ Password and Confirm Password do not match!", "danger")
            return redirect(url_for("index"))

    # Student extra fields
    student_id = request.form.get("student_id", "").strip()
    student_pass = request.form.get("student_password", "").strip()

    if not name:
        flash("⚠️ Name is required!", "warning")
        return redirect(url_for("index"))

    # Validate fields
    # Email + Password required for ALL roles (since student also enters them)
    if not email or not password:
        flash("⚠️ Email and Password are required!", "warning")
        return redirect(url_for("index"))

    if role == "student":
        student_id = request.form.get("student_id", "").strip()  # ✔ REAL ID (IT-5120)
        student_pass = request.form.get("student_password", "").strip()

        if not student_id or not student_pass:
            flash("⚠️ Student ID and Student Password are required!", "warning")
            return redirect(url_for("index"))

    # Select Firebase path
    if role == "admin":
        ref = db.reference("admins")
        # NEW → Admin must enter institute name
        if not institute_name:
            flash("⚠️ Institute / Organization name is required for Admin!", "warning")
            return redirect(url_for("index"))

    elif role == "teacher":
        ref = db.reference("teachers")
    elif role == "student":
        ref = db.reference("students_main")
    else:
        flash("Invalid role selected!", "danger")
        return redirect(url_for("index"))

    print(f"🔗 Selected Firebase path: {ref.path}")

    # ------------------------------
    # TEACHER SUBJECT PASS — NO VALIDATION
    if role == "teacher":
        subject_pass = request.form.get("subject_password", "").strip()

        if not subject_pass:
            flash("⚠️ Subject Password is required for Teacher!", "warning")
            return redirect(url_for("index"))
    else:
        subject_pass = ""

    # TEACHER SUBJECT PASSWORD VALIDATION (against admin → courses → subjects)
    if role == "teacher":
        admins = db.reference("admins").get() or {}
        valid_teacher = False
        found_course = None
        found_class = None
        found_subject = None


        for admin_id, admin_data in admins.items():
            courses = admin_data.get("courses", {})
            for course_id, course_data in courses.items():
                classes = course_data.get("classes", {})
                for class_key, class_data in classes.items():
                    subjects = class_data.get("subjects", {})
                    for subject_name, subject_data in subjects.items():

                        stored_pass = subject_data.get("password")
                        if stored_pass == subject_pass:
                            valid_teacher = True
                            found_admin_id = admin_id
                            found_course = course_id
                            found_class = class_key
                            found_subject = subject_name
                            break

                    if valid_teacher:
                        break
                if valid_teacher:
                    break
            if valid_teacher:
                break

        if not valid_teacher:
            flash("❌ Invalid Subject Password for Teacher!", "danger")
            return redirect(url_for("index"))

    # STUDENT PASSWORD VALIDATION (against admin → courses → classes → students)
    if role == "student":

        
        if not student_id or not student_pass:
            flash("⚠️ Student ID and Student Password are required!", "warning")
            return redirect(url_for("index"))

        admins = db.reference("admins").get() or {}
        valid_student = False

        found_admin_id = None
        found_course_id = None
        found_class_id = None

        for admin_id, admin_data in admins.items():
            courses = admin_data.get("courses", {})
            for course_id, course_data in courses.items():
                classes = course_data.get("classes", {})
                for class_id, class_data in classes.items():
                    students = class_data.get("students", {})
                    if student_id in students:
                        stored_pass = str(students.get(student_id, {}).get("password", "")).strip()
                        print("DEBUG → stored:", stored_pass, "| entered:", student_pass)  # Debug line
                        if stored_pass == student_pass.strip():
                            valid_student = True
                            found_admin_id = admin_id      # admin who owns this course
                            found_course_id = course_id    # student's course
                            found_class_id = class_id      # student's class
                            break

                if valid_student:
                    break
            if valid_student:
                break

        if not valid_student:
            flash("❌ Invalid Student ID or Student Password!", "danger")
            return redirect(url_for("index"))

    try:
        # Check if email already exists
        existing_users = ref.get() or {}
        for uid, data in existing_users.items():
            if data.get("email") == email:
                flash("⚠️ Email already registered! Please login.", "warning")
                return redirect(url_for("index"))

        # ------------------------------
        # ------------------------------
        if role == "student":
            # Fetch the institute name from the admin that owns this course/class  
            admins = db.reference("admins").get() or {}
            institute_name = admins[found_admin_id].get("institute_name", "Unknown")

            new_user = {
                "name": name,
                "email": email,
                "student_id": student_id,
                "student_pass": student_pass,
                "course": found_course_id,
                "class_key": found_class_id,
                "admin_id": found_admin_id,     # VERY IMPORTANT
                "institute_name": institute_name
            }



        elif role == "admin":
            new_user = {
                "name": name,
                "email": email,
                "password": password,
                "institute_name": institute_name,  # only admin gets this
                "courses": {},
                "students": {}
            }

        else:  # teacher
            new_user = {
                "name": name,
                "email": email,
                "password": password,
                "admin_id": found_admin_id,   # ⭐ ADD THIS LINE
                "course": found_course,
                "class_key": found_class,
                "subject": found_subject,
                "subject_pass": subject_pass
            }


        # ADD TEACHER SUBJECT DETAILS
        if role == "teacher":
            new_user["subject_pass"] = subject_pass
            new_user["course"] = found_course
            new_user["class_key"] = found_class
            new_user["subject"] = found_subject

        # Save user
        new_ref = ref.push(new_user)
        print(f"✅ User added under '{role}s' with ID {new_ref.key}")

        if role == "student":
            db.reference(
                f"admins/{found_admin_id}/courses/{found_course_id}/classes/{found_class_id}/students/{student_id}"
            ).set({
                "name": name,
                "password": student_pass
            })

        flash("✅ Signup successful! Please login.", "success")
        return redirect(url_for("index"))

    except Exception as e:
        print("❌ Firebase Error during signup:", e)
        flash("Signup failed! Try again later.", "danger")
        return redirect(url_for("index"))

# ----------------- Landing & Home Pages -----------------

@app.route("/home")  # Home page after landing
def home():
    return render_template("home.html", active="home")


@app.route('/feature')
def feature():
    return render_template('feature.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/help')
def help():
    return render_template('help.html')

# ----------------- Admin Login -----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    common_password = "smartmarkadmin123"
    if request.method == "POST":
        entered_password = request.form.get("password")
        if entered_password == common_password:
            session["admin_logged_in"] = True
            session["logged_in"] = True        # ← ADD THIS LINE
            session["role"] = "admin"

            session["admin_id"] = "admin_master"

            return redirect(url_for("admin_dashboard"))

        flash("Invalid password!", "danger")
    return render_template("admin_login.html")

# ----------------- Admin Add Course -----------------
@app.route("/admin_add_course", methods=["GET", "POST"])
def admin_add_course():
    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Please login as admin first!", "warning")
        return redirect(url_for("index"))

    admin_id = session.get("admin_id")
    if not admin_id:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("index"))

    courses_ref = db.reference(f"admins/{admin_id}/courses")
    courses_data = courses_ref.get() or {}

    if request.method == "POST":
        course_name = request.form.get("course_name")

        if not course_name or not course_name.strip():
            flash("Course name cannot be empty!", "danger")
            return redirect(url_for("admin_add_course"))

        course_name = course_name.strip()
        classes_input = request.form.getlist("classes[]")
        classes_input = [c.strip() for c in classes_input if c and c.strip()]

        if not classes_input:
            flash("Please add at least one class!", "danger")
            return redirect(url_for("admin_add_course"))

        # Make safe Firebase key
        safe_course_name = course_name.replace(".", "_").replace("$", "_")\
                                      .replace("#", "_").replace("[", "_")\
                                      .replace("]", "_").replace("/", "_")

        import time
        unique_course_key = safe_course_name + "_" + str(int(time.time()))

        classes_dict = {}
        for cls in classes_input:
            safe_cls = cls.replace(".", "_").replace("$", "_")\
                          .replace("#", "_").replace("[", "_")\
                          .replace("]", "_").replace("/", "_")
            classes_dict[safe_cls] = {
                "display_name": cls,
                "subjects": {},
                "password": None
            }

       # ✅ Save under this admin only (CHANGE HERE)
        courses_ref.child(unique_course_key).set({
            "name": course_name,
            "created_by": admin_id,   # ✅ add this line
            "classes": classes_dict
        })



        flash(f"Course '{course_name}' created successfully!", "success")
        return redirect(url_for("admin_add_subjects", course_key=unique_course_key))

    return render_template("admin_add_course.html", courses=courses_data)

# ----------------- Set Course/Class Password -----------------
@app.route("/set_course_password", methods=["POST"])
def set_course_password():
    if not session.get("admin_logged_in"):
        return "Unauthorized", 401

    course_key = request.form.get("course_key") or request.form.get("course_name")
    class_key = request.form.get("class_key")
    course_password = request.form.get("course_password") or request.form.get("password")

    if not course_key or not class_key or not course_password:
        return "Missing data", 400

    # Update password for that specific class under the course
    class_ref = db.reference(f"courses/{course_key}/classes/{class_key}")
    if class_ref.get() is None:
        return "Class not found", 404

    class_ref.update({"password": course_password})
    return "Password set successfully!", 200

# ----------------- Admin Select Course -----------------
@app.route("/admin_select_course")
def admin_select_course():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    # ✅ define admin_id before using it
    admin_id = session.get("admin_id")

    courses_ref = db.reference(f"admins/{admin_id}/courses")
    courses_data = courses_ref.get() or {}

    # ✅ Filter only the courses created by this admin
    courses_data = {
        code: data
        for code, data in courses_data.items()
        if data.get("created_by") == admin_id
    }

    # Ensure each course has "classes" key as dict
    for course_code, data in courses_data.items():
        if "classes" not in data or data["classes"] is None:
            data["classes"] = {}

        # Add course_code to data for easy linking later
        data["course_code"] = course_code
        # Add display name fallback
        data["display_name"] = data.get("name", course_code)

        # Add class_key inside each class for easy linking
        for class_key, class_data in data["classes"].items():
            class_data["class_key"] = class_key
            class_data["display_name"] = class_data.get("display_name", class_key)

    return render_template("admin_select_course.html", courses=courses_data)

# ----------------- Delete Course -----------------
@app.route("/delete_course/<course_code>")
def delete_course(course_code):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    courses_ref = db.reference("courses")
    courses_data = courses_ref.get() or {}

    if course_code in courses_data:
        courses_ref.child(course_code).delete()
        flash(f"✅ Course '{course_code}' deleted successfully!", "success")
    else:
        flash("⚠️ Course not found!", "error")

    return redirect(url_for("admin_select_course"))

# ----------------- Delete Class -----------------
@app.route("/delete_class/<course_code>/<class_key>")
def delete_class(course_code, class_key):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    class_ref = db.reference(f"courses/{course_code}/classes/{class_key}")
    if class_ref.get():
        class_ref.delete()
        flash(f"✅ Class '{class_key}' deleted successfully!", "success")
    else:
        flash("⚠️ Class not found!", "error")

    return redirect(url_for("admin_select_course"))

# ----------------- Edit Course -----------------
@app.route("/edit_course/<course_code>")
def edit_course(course_code):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    new_name = request.args.get("new_name", "").strip()
    if not new_name:
        flash("⚠️ No new name provided!", "error")
        return redirect(url_for("admin_select_course"))

    course_ref = db.reference(f"courses/{course_code}")
    if course_ref.get():
        course_ref.update({"name": new_name})
        flash(f"✏️ Course renamed to '{new_name}'", "success")
    else:
        flash("⚠️ Course not found!", "error")

    return redirect(url_for("admin_select_course"))

# ----------------- Edit Class -----------------
@app.route("/edit_class/<course_code>/<class_key>")
def edit_class(course_code, class_key):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    new_name = request.args.get("new_name", "").strip()
    if not new_name:
        flash("⚠️ No new name provided!", "error")
        return redirect(url_for("admin_select_course"))

    class_ref = db.reference(f"courses/{course_code}/classes/{class_key}")
    if class_ref.get():
        class_ref.update({"display_name": new_name})
        flash(f"✏️ Class renamed to '{new_name}'", "success")
    else:
        flash("⚠️ Class not found!", "error")

    return redirect(url_for("admin_select_course"))

# ----------------- Admin Dashboard -----------------
@app.route("/admin_dashboard")
def admin_dashboard():

    print("ADMIN DASHBOARD SESSION:", dict(session))

    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Please login as an admin first!", "warning")
        return redirect(url_for("index"))

    admin_id = session.get("admin_id")
    if not admin_id:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("index"))

    # ✅ Create a direct reference to this admin’s data
    admin_ref = db.reference(f"admins/{admin_id}")

    # ✅ Fetch only this admin’s private nodes
    admin_data = admin_ref.get() or {}
    courses = admin_ref.child("courses").get() or {}
    print("COURSES LOADED FOR THIS ADMIN:", courses)   # <-- ADD THIS LINE

    notices = admin_ref.child("notices").get() or {}

    reminders = admin_ref.child("reminders").get() or {}

    return render_template(
        "admin_dashboard.html",
        dept=session.get("admin_dept", "General"),
        admin=admin_data,
        courses=courses,
        notices=notices,
        reminders=reminders
    )

@app.route("/admin/select_course_for_manage_students")
def select_course_for_manage_students():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    courses = db.reference("courses").get() or {}
    
    return render_template("select_course.html", courses=courses)

@app.route("/admin/select_class_for_manage_students/<course_code>")
def select_class_for_manage_students(course_code):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    course = db.reference(f"courses/{course_code}/classes").get() or {}
    return render_template("select_class.html", course_code=course_code, classes=course)

# ----------------- Admin Add / Bulk Students -----------------
@app.route("/manage_students/<course_code>/<class_key>", methods=["GET", "POST"])

def manage_students(course_code, class_key):
    
    print("SESSION VALUES:", dict(session))
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    class_ref = db.reference(f"admins/{admin_id}/courses/{course_code}/classes/{class_key}")
    class_data = class_ref.get()


    if not class_data:
        flash("Class not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    students_ref = class_ref.child("students")
    all_students = students_ref.get() or {}

    # ✅ FILTER OUT SOFT-DELETED STUDENTS
    students = {
        roll: data
        for roll, data in all_students.items()
        if data.get("status") != "deleted"
    }

    # POST handling
    if request.method == "POST":
        # --- Bulk CSV Upload ---
        if 'csv_file' in request.files and request.files['csv_file'].filename != '':
            file = request.files['csv_file']
            reader = csv.DictReader(TextIOWrapper(file, encoding='utf-8'))
            added_students = []
            for row in reader:
                roll_no = row.get("roll_no", "").strip()
                name = row.get("name", "").strip()
                if not roll_no or roll_no in students:
                    continue
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                students_ref.child(roll_no).set({
                    "name": name,
                    "password": password,
                    "face_encodings": []
                })
                added_students.append(roll_no)
            flash(f"Added {len(added_students)} students successfully!", "success")
            return redirect(request.url)

        # --- Single Student Add ---
        roll_no = request.form.get("roll_no", "").strip()
        name = request.form.get("name", "").strip()
        if roll_no and name:
            if roll_no in students:
                flash(f"Roll No '{roll_no}' already exists!", "warning")
            else:
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                students_ref.child(roll_no).set({
                    "name": name,
                    "password": password,
                    "face_encodings": []
                })
                flash(f"Student '{roll_no}' added successfully!", "success")
            return redirect(request.url)

    # GET: render template
    return render_template(
        "manage_students.html",
        students=students,
        course_code=course_code,
        class_key=class_key
    )

# ----------------- Admin Manage Students Page (Course Selection) -----------------
@app.route("/admin/manage_students_page")
def manage_students_page():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    # Fetch all courses
    courses = db.reference("courses").get() or {}

    return render_template("manage_students_selection.html", courses=courses)

# ----------------- Admin Add Subjects -----------------
@app.route("/admin_add_subjects/<course_key>", methods=["GET", "POST"])
def admin_add_subjects(course_key):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    admin_email = session.get("email")
    admins = db.reference("admins").get() or {}
    admin_id = None
    for uid, data in admins.items():
        if data.get("email") == admin_email:
            admin_id = uid
            break

    if not admin_id:
        flash("Admin not found. Please login again.", "danger")
        return redirect(url_for("admin_login"))

    # ✅ Use this admin’s private course path
    course_ref = db.reference(f"admins/{admin_id}/courses/{course_key}")
    course_data = course_ref.get()

    if not course_data:
        flash("Course not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    classes = course_data.get("classes", {}) or {}

    if request.method == "POST":
        class_key = request.form.get("class_key")
        subject_name = request.form.get("subject")

        if not class_key or not subject_name:
            flash("Please provide class and subject name.", "danger")
            return redirect(url_for("admin_add_subjects", course_key=course_key))

        subject_password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

        subject_data = {
            "password": subject_password,
            "attendance": {}
        }

        # ✅ Save under this admin’s node
        course_ref.child("classes").child(class_key).child("subjects").update({
            subject_name: subject_data
        })

        flash(
            f"Subject '{subject_name}' added to class '{classes[class_key]['display_name']}' "
            f"with password: {subject_password}", "success"
        )
        return redirect(url_for("admin_add_subjects", course_key=course_key))

    flash_messages = [(c, m) for c, m in session.get('_flashes', [])] if '_flashes' in session else []

    return render_template(
        "admin_add_subjects.html",
        course_key=course_key,
        course_name=course_data.get("name", "Unknown"),
        classes=classes,
        flash_messages=flash_messages
    )

# ----------------- Admin Add Students (renamed to avoid duplicate endpoint) -----------------
@app.route("/admin_add_students/<course_key>/<class_key>", methods=["GET", "POST"])
def add_students(course_key, class_key):  # <- renamed from admin_add_students
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    courses_ref = db.reference("courses")
    course_ref = courses_ref.child(course_key)
    course_data = course_ref.get()
    if not course_data:
        flash("Course not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    classes = course_data.get("classes", {}) or {}
    if class_key not in classes:
        flash("Class not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    class_name = classes[class_key]["display_name"]

    if request.method == "POST":
        if 'csv_file' not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file = request.files['csv_file']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(request.url)

        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            csv_input = csv.DictReader(stream)
            students_ref = course_ref.child(f"classes/{class_key}/students")

            added_count = 0
            for row in csv_input:
                roll_no = row.get("RollNo", "").strip()
                name = row.get("StudentName", "").strip()
                if roll_no and name:
                    # Auto-generate 8-character password
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    students_ref.child(roll_no).set({
                        "name": name,
                        "roll_no": roll_no,
                        "password": password,
                        "class": class_key,
                        "face_encodings": None
                    })
                    added_count += 1

            flash(f"{added_count} students added successfully!", "success")

        except Exception as e:
            flash(f"Error processing CSV: {e}", "danger")
            return redirect(request.url)

    flash_messages = [(category, msg) for category, msg in session.get('_flashes', [])] if '_flashes' in session else []

    return render_template(
        "manage_students.html",
        course_name=course_data.get("name", "Unknown"),
        class_name=class_name,
        flash_messages=flash_messages
    )

# ----------------- Edit a Student -----------------
@app.route("/admin/edit_student/<course_code>/<class_key>/<roll_no>", methods=["POST"])
def edit_student(course_code, class_key, roll_no):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    students_ref = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{class_key}/students"
    )

    student = students_ref.child(roll_no).get()
    if not student or student.get("status") == "deleted":
        flash("Student not found!", "danger")
        return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

    # 🔹 NEW VALUES
    new_roll = request.form.get("roll_no", "").strip()
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "").strip()

    if not new_roll or not name or not password:
        flash("All fields are required!", "warning")
        return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

    # =================================================
    # CASE 1️⃣ Roll number NOT changed
    # =================================================
    if new_roll == roll_no:
        students_ref.child(roll_no).update({
            "name": name,
            "password": password
        })
        flash(f"Student {roll_no} updated successfully!", "success")

    # =================================================
    # CASE 2️⃣ Roll number CHANGED
    # =================================================
    else:
        # Prevent duplicate roll numbers
        if students_ref.child(new_roll).get():
            flash(f"Roll number {new_roll} already exists!", "danger")
            return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

        # 🔁 Copy data
        updated_student = student.copy()
        updated_student.update({
            "name": name,
            "password": password
        })

        # Create new node
        students_ref.child(new_roll).set(updated_student)

        # Delete old node
        students_ref.child(roll_no).delete()

        flash(f"Student updated successfully (Roll changed from {roll_no} → {new_roll})", "success")

    return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

# ----------------- Delete a Student -----------------
from datetime import datetime

@app.route("/admin/delete_student/<course_code>/<class_key>/<roll_no>", methods=["POST"])
def delete_student(course_code, class_key, roll_no):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    students_ref = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{class_key}/students"
    )

    student = students_ref.child(roll_no).get()

    if student:
        students_ref.child(roll_no).delete()
        flash(f"Student {roll_no} deleted successfully!", "success")
    else:
        flash("Student not found!", "danger")

    return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

@app.route("/admin_exit_add_subjects")
def admin_exit_add_subjects():
    # Clear any flashed messages
    session.pop('_flashes', None)
    # Redirect to dashboard
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/reset_student_password/<course_code>/<class_key>/<roll_no>", methods=["POST"])
def reset_student_password(course_code, class_key, roll_no):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    students_ref = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{class_key}/students"
    )

    student = students_ref.child(roll_no).get()
    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

    # 🔐 Generate new system password
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    # ✅ Update password + metadata
    students_ref.child(roll_no).update({
        "password": new_password,
        "password_reset_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "password_reset_by": "admin"
    })

    flash(f"Password for {roll_no} reset successfully!", "success")
    flash(f"New Password: {new_password}", "info")

    return redirect(url_for("manage_students", course_code=course_code, class_key=class_key))

@app.route("/admin/export_students_csv/<course_code>/<class_key>")
def export_students_csv(course_code, class_key):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    students_ref = db.reference(f"courses/{course_code}/classes/{class_key}/students")
    students = students_ref.get() or {}

    def generate_csv():
        yield "RollNo,StudentName,Password\n"
        for roll, data in students.items():
            yield f"{roll},{data.get('name','')},{data.get('password','')}\n"

    return Response(generate_csv(), mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename={course_code}_{class_key}_students.csv"})

from datetime import datetime
from firebase_admin import db
from flask import request, redirect, url_for, render_template, session

# =========================
# MANAGE COURSES PAGE
# =========================
@app.route("/admin/manage-courses")
def admin_manage_courses():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    # Firebase structure:
    # admins/{admin_id}/courses/{course_code}
    courses_ref = db.reference(f"admins/{admin_id}/courses")
    courses = courses_ref.get() or {}

    return render_template(
        "admin_manage_courses.html",
        courses=courses
    )

# =========================
# ADD CLASS
# =========================
@app.route("/add_class", methods=["POST"])
def add_class():
    admin_id = session["admin_id"]

    course_code = request.form["course_code"]
    class_name = request.form["class_name"]

    class_key = class_name.lower().replace(" ", "_")

    db.child("courses").child(admin_id)\
      .child(course_code)\
      .child("classes")\
      .child(class_key)\
      .set({
        "name": class_name,
        "subjects": {}
      })

    return redirect(url_for("manage_courses"))

import uuid

@app.route("/add_subject", methods=["POST"])
def add_subject():
    admin_id = session["admin_id"]

    course_code = request.form["course_code"]
    class_key = request.form["class_key"]
    subject_name = request.form["subject_name"]

    subject_id = str(uuid.uuid4())[:8]

    db.child("courses").child(admin_id)\
      .child(course_code)\
      .child("classes")\
      .child(class_key)\
      .child("subjects")\
      .child(subject_id)\
      .set({
        "name": subject_name
      })

    return redirect(url_for("manage_courses"))

# =========================
# ADD SUBJECT (SAFE)
# =========================
@app.route('/admin/add-subject', methods=["POST"])
def admin_add_subject_new():
    admin_id = session.get("admin_id")
    course_code = request.form["course_code"]
    class_key = request.form["class_key"]
    subject = request.form["subject"]

    db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{class_key}/subjects/{subject}"
    ).set({
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    return redirect(url_for("admin_manage_courses"))

# =========================
# DELETE SUBJECT (SAFE)
# =========================
@app.route("/delete_subject", methods=["POST"])
def delete_subject():
    admin_id = session["admin_id"]

    course_code = request.form["course_code"]
    class_key = request.form["class_key"]
    subject_id = request.form["subject_id"]

    db.child("courses").child(admin_id)\
      .child(course_code)\
      .child("classes")\
      .child(class_key)\
      .child("subjects")\
      .child(subject_id)\
      .remove()

    return redirect(url_for("manage_courses"))

# ------------------ ADMIN VIEW ATTENDANCE ------------------

from flask import jsonify, request

from collections import defaultdict

@app.route('/admin/view_attendance/<course>/<class_key>', methods=['GET'])
def admin_view_attendance(course, class_key):

    # ---- AUTH CHECK ----
    if 'admin_logged_in' not in session:
        flash("Please log in as Admin to access attendance view.", "danger")
        return redirect(url_for('admin_login'))

    admin_id = session.get("admin_id")
    if not admin_id:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("admin_login"))

    attendance_ref = db.reference(f"attendance/{admin_id}")
    attendance_data = attendance_ref.get() or {}

    # =========================================================
    # 1️⃣ FETCH LIVE SESSIONS  → THIS DEFINES TOTAL LECTURES
    # =========================================================
    live_ref = db.reference(f"live_sessions/{admin_id}")
    live_sessions = live_ref.get() or {}

    relevant_sessions = []

    # live_sessions/{admin_id}/{course}/{class_key}/{subject}
    if course in live_sessions:
        course_data = live_sessions[course]

        if class_key in course_data:
            class_data = course_data[class_key]

            # each subject here represents one lecture session
            for subject in class_data:
                relevant_sessions.append(subject)

    total_lectures = 0

    if course in attendance_data and class_key in attendance_data[course]:
        for subject, dates in attendance_data[course][class_key].items():
            for date, lecture_instances in dates.items():
                total_lectures += len(lecture_instances)

    # =========================================================
    # 2️⃣ FETCH ATTENDANCE  → THIS DEFINES PRESENT
    # =========================================================

    present_map = defaultdict(int)
    last_seen_map = {}

    if course in attendance_data and class_key in attendance_data[course]:
        for subject, dates in attendance_data[course][class_key].items():
            for date, lecture_instances in dates.items():
                for lecture_id, students_present in lecture_instances.items():
                    for sid, info in students_present.items():
                        present_map[sid] += 1
                        if isinstance(info, dict):
                            last_seen_map[sid] = info.get("timestamp", "N/A")
                        else:
                            last_seen_map[sid] = "N/A"

    # =========================================================
    # 3️⃣ FETCH STUDENTS (MASTER LIST)
    # =========================================================
    students_ref = db.reference(
        f"admins/{admin_id}/courses/{course}/classes/{class_key}/students"
    )
    students = students_ref.get() or {}

    # =========================================================
    # 4️⃣ BUILD TABLE DATA
    # =========================================================
    table_data = []

    for sid, info in students.items():
        present = present_map.get(sid, 0)
        total = total_lectures
        absent = max(total - present, 0)
        percentage = round((present / total) * 100, 2) if total > 0 else 0

        if total == 0:
            status = "No Data"
        elif percentage >= 75:
            status = "Regular"
        elif percentage >= 50:
            status = "At Risk"
        else:
            status = "Critical"

        table_data.append({
            "sid": sid,
            "name": info.get("name", "Unknown"),
            "present": present,
            "absent": absent,
            "total": total,
            "percentage": percentage,
            "last_seen": last_seen_map.get(sid, "N/A"),
            "status": status
        })

    print("PRESENT MAP:", present_map)
    print("TOTAL LECTURES:", total_lectures)

    # =========================================================
    # 5️⃣ RENDER PAGE
    # =========================================================
    return render_template(
        "admin_view_attendance.html",
        table_data=table_data,
        course=course,
        class_key=class_key
    )

from datetime import datetime
from collections import defaultdict

@app.route('/admin/attendance/edit', methods=['POST'])
def admin_edit_attendance():

    if 'admin_logged_in' not in session:
        return jsonify(success=False), 401

    data = request.get_json()
    admin_id = session.get("admin_id")

    class_key = data['class_key']
    student_id = data['student_id']
    new_present = int(data['present'])

    attendance_ref = db.reference(f"attendance/{admin_id}")
    attendance_data = attendance_ref.get() or {}

    present_nodes = []
    absent_nodes = []

    # ✅ COLLECT LECTURE INSTANCES (CORRECT LEVEL)
    for session_id, session_data in attendance_data.items():
        if class_key not in session_data:
            continue

        for subject, dates in session_data[class_key].items():
            for date, lecture_instances in dates.items():
                for lecture_id, students_present in lecture_instances.items():

                    node = (session_id, subject, date, lecture_id)

                    if student_id in students_present:
                        present_nodes.append(node)
                    else:
                        absent_nodes.append(node)

    current_present = len(present_nodes)
    diff = new_present - current_present

    # ✅ INCREASE PRESENT (ADD TO ABSENT LECTURES)
    if diff > 0:
        for session_id, subject, date, lecture_id in absent_nodes:
            if diff == 0:
                break

            db.reference(
                f"attendance/{admin_id}/{session_id}/{class_key}/{subject}/{date}/{lecture_id}/{student_id}"
            ).set({
                "timestamp": datetime.now().isoformat(),
                "edited_by": admin_id,
                "edit_type": "ADMIN_ADD"
            })

            diff -= 1

    # ✅ DECREASE PRESENT (REMOVE FROM PRESENT LECTURES)
    elif diff < 0:
        for session_id, subject, date, lecture_id in reversed(present_nodes):
            if diff == 0:
                break

            db.reference(
                f"attendance/{admin_id}/{session_id}/{class_key}/{subject}/{date}/{lecture_id}/{student_id}"
            ).delete()

            diff += 1

    return jsonify(success=True)

@app.route('/admin/attendance/delete', methods=['POST'])
def admin_delete_attendance():

    if 'admin_logged_in' not in session:
        return jsonify(success=False), 401

    data = request.get_json()
    admin_id = session.get("admin_id")

    class_key = data['class_key']
    student_id = data['student_id']

    attendance_ref = db.reference(f"attendance/{admin_id}")
    attendance_data = attendance_ref.get() or {}

    # ✅ DELETE STUDENT FROM ALL LECTURE INSTANCES
    for session_id, session_data in attendance_data.items():
        if class_key not in session_data:
            continue

        for subject, dates in session_data[class_key].items():
            for date, lecture_instances in dates.items():
                for lecture_id in lecture_instances:

                    db.reference(
                        f"attendance/{admin_id}/{session_id}/{class_key}/{subject}/{date}/{lecture_id}/{student_id}"
                    ).delete()

    return jsonify(success=True)

@app.route("/admin/select_attendance")
def admin_select_attendance():
    if "admin_logged_in" not in session:
        flash("Please login as admin.", "danger")
        return redirect(url_for("admin_login"))

    # Fetch all courses created by admin
    admin_id = session.get("admin_id")

    if not admin_id:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("admin_login"))

    courses = db.reference(f"admins/{admin_id}/courses").get() or {}


    return render_template("admin_select_attendance.html", courses=courses)

@app.route('/admin/attendance/student/<course>/<class_key>/<student_id>')
def admin_student_subject_attendance(course, class_key, student_id):

    if 'admin_logged_in' not in session:
        return jsonify([]), 401

    admin_id = session.get("admin_id")

    attendance_ref = db.reference(f"attendance/{admin_id}")
    attendance_data = attendance_ref.get() or {}

    subject_map = {}

    if course in attendance_data and class_key in attendance_data[course]:
        for subject, dates in attendance_data[course][class_key].items():
            total = 0
            present = 0

            for date, lectures in dates.items():
                for lecture_id, students in lectures.items():
                    total += 1
                    if student_id in students:
                        present += 1

            if total > 0:
                subject_map[subject] = {
                    "present": present,
                    "total": total,
                    "percentage": round((present / total) * 100, 2)
                }

    return jsonify(subject_map)

# ------------------ EXPORT ATTENDANCE CSV ------------------
@app.route('/admin/export-attendance/<course>/<class_key>/<subject>')
def export_attendance_csv(course, class_key, subject):
    # Fetch attendance data from Firebase
    attendance_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance")
    attendance_data = attendance_ref.get() or {}

    # Build attendance table data
    student_attendance = {}
    for date, records in attendance_data.items():
        for student_id, status in records.items():
            if student_id not in student_attendance:
                student_attendance[student_id] = {'present': 0, 'total': 0}
            student_attendance[student_id]['total'] += 1
            if status == "Present":
                student_attendance[student_id]['present'] += 1

    # Fetch student details
    students_ref = db.reference(f"courses/{course}/classes/{class_key}/students")
    students = students_ref.get() or {}

    # Create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Student Name", "Present", "Total Classes", "Percentage (%)"])

    for sid, info in students.items():
        present = student_attendance.get(sid, {}).get('present', 0)
        total = student_attendance.get(sid, {}).get('total', 0)
        percentage = round((present / total) * 100, 2) if total > 0 else 0
        writer.writerow([sid, info.get("name", ""), present, total, percentage])

    output.seek(0)

    # Send as downloadable file
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{course}_{subject}_attendance.csv"
    )


@app.route('/admin/export-attendance-detailed/<course>/<class_key>/<subject>')
def export_attendance_csv_detailed(course, class_key, subject):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    import io
    import csv
    from flask import send_file

    # Fetch students
    students_ref = db.reference(f"courses/{course}/classes/{class_key}/students")
    students = students_ref.get() or {}

    # Fetch attendance records
    attendance_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance")
    attendance_data = attendance_ref.get() or {}

    # Build table data
    table_data = []
    for sid, info in students.items():
        present = 0
        total = 0
        for date, records in attendance_data.items():
            total += 1
            if records.get(sid) == "Present":
                present += 1
        percentage = round((present / total) * 100, 2) if total > 0 else 0
        table_data.append({
            "roll_no": info.get("roll_no"),
            "name": info.get("name"),
            "present": present,
            "total": total,
            "percentage": percentage
        })

    # Create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll No", "Name", "Present", "Total Classes", "Percentage (%)"])
    for student in table_data:
        writer.writerow([student["roll_no"], student["name"], student["present"], student["total"], student["percentage"]])

    output.seek(0)

    # Send as downloadable file
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{course}_{class_key}_{subject}_attendance.csv"
    )

# ----------------- Admin Course Dashboard -----------------
@app.route("/admin_course_dashboard/<course_key>", methods=["GET", "POST"])
def admin_course_dashboard(course_key):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    courses_ref = db.reference("courses")
    course_data = courses_ref.child(course_key).get()

    if not course_data:
        flash("Course not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        class_key = request.form.get("class_key")
        subject_name = request.form.get("subject")
        class_password = request.form.get("class_password")

        if class_key and subject_name:
            if "subjects" not in course_data["classes"][class_key]:
                course_data["classes"][class_key]["subjects"] = {}
            course_data["classes"][class_key]["subjects"][subject_name] = []
            courses_ref.child(course_key).child("classes").child(class_key).update({
                "subjects": course_data["classes"][class_key]["subjects"]
            })
            flash(f"Subject '{subject_name}' added to class '{class_key}'", "success")

        if class_key and class_password:
            courses_ref.child(course_key).child("classes").child(class_key).update({
                "password": class_password
            })
            flash(f"Password set for class '{class_key}'", "success")

        return redirect(url_for("admin_course_dashboard", course_key=course_key))

    return render_template("admin_course_dashboard.html", course_key=course_key, course=course_data)

@app.route("/admin_settings")
def admin_settings():
    if not (session.get("admin_logged_in") or session.get("role") == "admin"):
        flash("Please login first.", "warning")
        return redirect(url_for("admin_login"))
    # Render your admin settings page
    return render_template("admin_settings.html")

@app.route("/admin/portion_completion")
def admin_portion_completion():
    if "admin_logged_in" not in session:
        flash("Please login as admin!", "danger")
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    # 🔹 Get only the logged-in admin’s courses
    courses_ref = db.reference(f"admins/{admin_id}/courses")
    admin_courses = courses_ref.get() or {}

    # Final structured data to send to HTML
    portion_table = []

    for course_code, course_data in admin_courses.items():
        classes = course_data.get("classes", {})

        for class_key, class_data in classes.items():
            subjects = class_data.get("subjects", {})

            for subject_name, subject_data in subjects.items():
                portion_entries = subject_data.get("portion_completed", []) or []

                # New values from teacher page
                total_chapters = subject_data.get("total_chapters")
                completed_chapters = subject_data.get("completed_chapters", 0)

                # Completed chapters count
                completed_count = completed_chapters

                # Pending chapters
                pending_count = (total_chapters - completed_chapters) if total_chapters else "N/A"

                # Progress percentage
                if total_chapters:
                    progress_percent = round((completed_chapters / total_chapters) * 100)
                else:
                    progress_percent = 0

                # Latest update timestamp
                if portion_entries:
                    last_updated = max(entry.get("timestamp", "") for entry in portion_entries)
                else:
                    last_updated = "No updates"

                teacher_name = subject_data.get("teacher", "Unknown")

                # Store all rows
                portion_table.append({
                    "course": course_code,
                    "class": class_key,
                    "subject": subject_name,
                    "teacher": teacher_name,
                    "completed": completed_count,
                    "total": total_chapters,
                    "pending": pending_count,
                    "percent": progress_percent,
                    "last_updated": last_updated,
                    "entries": portion_entries,   # for slide-panel
                    "completed_chapters": completed_count
                })

    return render_template(
        "admin_portion_completion.html",
        portion_table=portion_table
    )

from datetime import datetime, timedelta

def passes_date_filter(timestamp_str, date_range):
    """
    timestamp_str expected "YYYY-MM-DD HH:MM"
    date_range: "", "7", "30", "month", "year"
    """
    if not date_range or date_range == "":
        return True

    try:
        notice_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
    except Exception:
        # If timestamp parsing fails, treat it as passing the filter
        return True

    now = datetime.now()

    if date_range == "7":
        return notice_time >= now - timedelta(days=7)
    if date_range == "30":
        return notice_time >= now - timedelta(days=30)
    if date_range == "month":
        return notice_time.month == now.month and notice_time.year == now.year
    if date_range == "year":
        return notice_time.year == now.year

    return True

from flask import request, session, redirect, url_for, flash
@app.route("/upload_notice_admin", methods=["POST"])
def upload_notice_admin():
    if "admin_id" not in session:
        flash("Please login as admin.", "error")
        return redirect(url_for("home"))

    admin_id = session["admin_id"]
    admin_name = session.get("admin_name", "Admin")

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    audience = request.form.get("audience", "both")
    status = request.form.get("status", "published")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    notice_id = db.reference("notices").push().key
    
    notice_data = {
        "id": notice_id,
        "title": title,
        "body": body,
        "posted_by": admin_name, 
        "uploader_role": "admin",
        "uploader_name": admin_name,
        "admin_id": admin_id,
        "course": "all",
        "class_key": "all",
        "audience": audience,
        "status": status,
        "timestamp": timestamp
    }

    db.reference("notices").push(notice_data)

    flash("Announcement posted to all classes.", "success")
    return redirect(url_for("admin_announcements"))

# Admin posting notice using firebase_admin
from firebase_admin import db
from datetime import datetime

@app.route("/admin_announcements")
def admin_announcements():
    if "admin_id" not in session:
        flash("Please login.", "error")
        return redirect(url_for("home"))

    # GET FILTER VALUES
    search = request.args.get("search", "").lower().strip()
    date_range = request.args.get("date_range", "")
    audience = request.args.get("audience", "")
    status = request.args.get("status", "")

    # FETCH ALL NOTICES
    notices_ref = db.reference("notices").get() or {}

    # include Firebase ID in each notice
    notices = []
    for key, value in notices_ref.items():
        if isinstance(value, dict):   # <-- ADD THIS CHECK
            notices.append({"id": key, **value})
        else:
            print(f"⚠️ Skipping invalid notice at key {key}: not a dict")

    # --------------------------------
    # 🔍 1. SEARCH FILTER
    # --------------------------------
    if search:
        notices = [
            n for n in notices
            if search in n.get("title", "").lower()
            or search in n.get("body", "").lower()
        ]

    # --------------------------------
    # 📅 2. DATE RANGE FILTER
    # --------------------------------
    if date_range:
        now = datetime.now()

        def within_range(ts, days=None):
            try:
                nt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
                if days:
                    return (now - nt).days <= int(days)
                elif date_range == "month":
                    return nt.month == now.month and nt.year == now.year
                elif date_range == "year":
                    return nt.year == now.year
            except:
                return False

        if date_range in ("7", "30"):
            notices = [n for n in notices if within_range(n.get("timestamp", ""), days=date_range)]
        else:
            notices = [n for n in notices if within_range(n.get("timestamp", ""))]

    # --------------------------------
    # 🎯 3. AUDIENCE FILTER
    # --------------------------------
    if audience:
        notices = [
            n for n in notices
            if n.get("audience") == audience or n.get("audience") == "both"
        ]

    # --------------------------------
    # 📌 4. STATUS FILTER
    # --------------------------------
    if status:
        notices = [n for n in notices if n.get("status") == status]

    # SORT NEWEST FIRST
    notices.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return render_template(
        "admin_announcements.html",
        notices=notices
    )

@app.route("/delete_admin_notice", methods=["POST"])
def delete_admin_notice():
    if "admin_id" not in session:
        return redirect(url_for("home"))

    notice_id = request.form.get("notice_id")

    if notice_id:
        db.reference(f"notices/{notice_id}").delete()

    flash("Notice deleted successfully!", "success")
    return redirect(url_for("admin_announcements"))

@app.route("/admin_schedule")
def admin_schedule():

    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("index"))

    admin_id = session.get("admin_id")

    admin_ref = db.reference(f"admins/{admin_id}")
    courses = admin_ref.child("courses").get() or {}

    # Get all classes from all courses
    class_list = []
    subjects_map = {}  # { "FYBAF": ["Eco", "Maths"], ... }
    schedule = {} 

    for course_id, course_data in courses.items():
        classes = course_data.get("classes", {})
        for class_key, cdata in classes.items():
            # Get all classes from all courses (FIXED)
            class_list = []
            subjects_map = {}

            for course_id, course_data in courses.items():
                classes = course_data.get("classes", {}) or {}

                for class_key, cdata in classes.items():

                    # unique class per course
                    unique_class_id = f"{course_id}__{class_key}"

                    # label shown in dropdown
                    label = f"{class_key} ({course_data.get('name', '')})"

                    class_list.append({
                        "id": unique_class_id,
                        "label": label
                    })

                    subjects_node = cdata.get("subjects", {}) or {}
                    subjects_map[unique_class_id] = list(subjects_node.keys())

                    print(f"DEBUG {unique_class_id} subjects:", subjects_node)

    # Fetch teachers for this admin
    teachers_ref = db.reference("teachers")
    all_teachers = teachers_ref.get() or {}

    # Filter teachers belonging to this admin ONLY
    teachers = {
        tid: tdata
        for tid, tdata in all_teachers.items()
        if tdata.get("admin_id") == admin_id
    }

    schedule_ref = db.reference(f"admins/{admin_id}/schedule")
    raw_schedule = schedule_ref.get() or {}

    organized_schedule = {
        "Monday": {},
        "Tuesday": {},
        "Wednesday": {},
        "Thursday": {},
        "Friday": {},
        "Saturday": {}
    }

    for lec_id, lec in raw_schedule.items():
        day = lec.get("day")
        if day in organized_schedule:
            organized_schedule[day][lec_id] = lec

    return render_template(
        "admin_schedule.html",
        class_list=class_list,
        subjects=subjects_map,
        teachers=teachers,
        schedule=organized_schedule      # ✅ CORRECT
    )

@app.route("/admin_schedule_save", methods=["POST"])
def admin_schedule_save():
    if not session.get("logged_in") or session.get("role") != "admin":
        return "Unauthorized", 403

    admin_id = session.get("admin_id")
    admin_ref = db.reference(f"admins/{admin_id}")

    data = request.form

    course_id, class_key = data.get("class").split("__")
    subject = data.get("subject")
    teacher = data.get("teacher")

    teacher_name = data.get("teacher")

    teachers_ref = db.reference("teachers")
    all_teachers = teachers_ref.get() or {}

    teacher_id = None
    for tid, tdata in all_teachers.items():
        if (
            tdata.get("name") == teacher_name and
            tdata.get("admin_id") == admin_id
        ):
            teacher_id = tid
            break

    # 🔐 SAFETY: ensure teacher_id exists (for teacher schedule)
    if not teacher_id:
        flash("Invalid teacher name. Lecture not saved.", "error")
        return redirect(url_for("admin_schedule"))

    lecture_data = {
        "class": session.get("class_key"),          # ✅ FIXED source
        "course": session.get("course"),            # 🔴 REQUIRED
        "course_id": course_id,
        "class": class_key,
        "teacher_key": f"{teacher}__{subject}",
        "teacher_id": teacher_id,
        "subject": data.get("subject"),
        "teacher": data.get("teacher"),
        "day": data.get("day"),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "room": data.get("room"),
        "admin_id": admin_id
    }


    # Save lecture under schedule root (NOT inside class)
    lec_id = data.get("lec_id")

    if lec_id:
        # UPDATE existing lecture
        admin_ref.child(f"schedule/{lec_id}").update(lecture_data)
    else:
        # CREATE new lecture
        admin_ref.child("schedule").push(lecture_data)


    flash("Lecture saved successfully!", "success")
    return redirect(url_for("admin_schedule"))

@app.route("/admin_schedule_delete/<lec_id>", methods=["POST"])
def admin_schedule_delete(lec_id):
    if not session.get("logged_in") or session.get("role") != "admin":
        return {"success": False}, 403

    admin_id = session.get("admin_id")

    # 🔥 DELETE FROM SINGLE SOURCE OF TRUTH
    db.reference(f"admins/{admin_id}/schedule/{lec_id}").delete()

    return {"success": True}

@app.route("/admin_schedule_update", methods=["POST"])
def admin_schedule_update():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("index"))

    admin_id = session.get("admin_id")
    lec_id = request.form.get("lec_id")

    course_id, class_key = request.form["class"].split("__")

    subject = request.form["subject"]
    teacher = request.form["teacher"]

    lecture_data = {
        "course_id": course_id,
        "class": class_key,
        "subject": subject,
        "teacher": teacher,
        "teacher_key": f"{teacher}__{subject}",
        "subject": request.form["subject"],
        "teacher": request.form["teacher"],
        "day": request.form["day"],
        "start_time": request.form["start_time"],
        "end_time": request.form["end_time"],
        "room": request.form["room"]
    }

    db.reference(f"admins/{admin_id}/schedule/{lec_id}").update(lecture_data)

    flash("Lecture updated successfully!", "success")
    return redirect(url_for("admin_schedule"))

import uuid
from datetime import datetime

@app.route("/admin/add_reminder", methods=["POST"])
def admin_add_reminder():
    if "admin_id" not in session:
        return redirect(url_for("index"))

    admin_id = session["admin_id"]

    reminder_id = str(uuid.uuid4())

    db.reference(f"admins/{admin_id}/reminders/{reminder_id}").set({
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "type": request.form.get("type"),
        "date": request.form.get("date"),
        "time": request.form.get("time"),
        "created_at": int(datetime.now().timestamp())
    })

    return redirect(url_for("admin_dashboard"))

import csv, random, string
from io import TextIOWrapper

# ---------------- Logout ----------------
@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

# ----------------- Teacher Login -----------------
@app.route("/teacher_login", methods=["POST"])
def teacher_login():
    # --- ORIGINAL CODE (commented temporarily for testing) ---
    """
    teacher_name = (request.form.get("teacher_name") or "").strip()
    subject_password = (request.form.get("subject_password") or "").strip()

    if not teacher_name or not subject_password:
        flash("Please enter all required fields.", "danger")
        return redirect(url_for("home"))

    courses_ref = db.reference("courses")
    courses_data = courses_ref.get() or {}

    matched_course = None
    matched_class = None
    matched_subject = None

    # Search for password
    for course_key, course_info in courses_data.items():
        classes = course_info.get("classes", {}) or {}
        if isinstance(classes, list):
            classes = {str(i): c for i, c in enumerate(classes)}

        for class_key, class_info in classes.items():
            subjects = class_info.get("subjects", {}) or {}
            if isinstance(subjects, list):
                subjects = {str(i): s for i, s in enumerate(subjects)}

            for subject_name, subject_info in subjects.items():
                if subject_info.get("password") == subject_password:
                    matched_course = course_key
                    matched_class = class_key
                    matched_subject = subject_name
                    break
            if matched_course:
                break
        if matched_course:
            break

    if not matched_course:
        flash("Invalid Subject Password!", "danger")
        return redirect(url_for("home"))

    session["teacher"] = teacher_name
    session["course"] = matched_course
    session["class_key"] = matched_class
    session["subject"] = matched_subject
    return redirect(url_for("teacher_dashboard"))
    """

    # --- TESTING CODE (temporary) ---
    session["teacher"] = "Test Teacher"
    session["course"] = "Test Course"
    session["class_key"] = "Test Class"
    session["subject"] = "Test Subject"
    return redirect(url_for("teacher_dashboard"))

# ----------------- Teacher Dashboard -----------------
@app.route('/teacher_dashboard')
def teacher_dashboard():
    # ✅ Fix login check
    if not session.get("logged_in") or session.get("role") != "teacher":
        flash("Please log in as a teacher first.", "warning")
        return redirect(url_for("index"))

    # ✅ Identify logged-in teacher
    teacher_email = session.get("email")
    if not teacher_email:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("index"))

    # ✅ Fetch teacher data from Firebase
    teachers = db.reference("teachers").get() or {}
    teacher_data = None
    for tid, tdata in teachers.items():
        if tdata.get("email") == teacher_email:
            teacher_data = tdata
            break

    if not teacher_data:
        flash("Teacher data not found!", "danger")
        return redirect(url_for("index"))

    # ✅ Get the teacher’s assigned course/class/subject
    course = teacher_data.get("course")
    class_key = teacher_data.get("class_key")
    subject = teacher_data.get("subject")

    # ✅ Fetch only their students
    students_ref = db.reference(
        f"admins/{teacher_data.get('admin_id')}/courses/{course}/classes/{class_key}/students"
    )

    students = students_ref.get() or {}

    return render_template(
        'teacher_dashboard.html',
        teacher=teacher_data,
        course=course,
        class_key=class_key,
        subject=subject,
        students=students
    )

# ----------------- Teacher View/Edit Attendance -----------------
@app.route('/view_student_data')
def view_student_data():

    if 'teacher' not in session:
        return redirect(url_for('teacher_login'))

    admin_id = session.get("admin_id")
    course = session.get('course')
    class_key = session.get('class_key')
    subject = session.get('subject')

    # -------------------------------------------------
    # 1️⃣ Fetch students (master list)
    # -------------------------------------------------
    students_ref = db.reference(
        f"admins/{admin_id}/courses/{course}/classes/{class_key}/students"
    )
    raw_students = students_ref.get() or {}

    students = {
        sid: info
        for sid, info in raw_students.items()
        if info.get("status") != "deleted"
    }

    # -------------------------------------------------
    # 2️⃣ Fetch attendance (admin source)
    # -------------------------------------------------
    attendance_ref = db.reference(f"attendance/{admin_id}")
    attendance_data = attendance_ref.get() or {}

    # -------------------------------------------------
    # 3️⃣ Build lecture timeline (FIXED ORDER)
    # -------------------------------------------------
    lecture_keys = []
    subject_data = {}

    if course in attendance_data and class_key in attendance_data[course]:
        subject_data = attendance_data[course][class_key].get(subject, {})

        for date, lecture_instances in subject_data.items():
            for lecture_id in lecture_instances:
                lecture_keys.append((date, lecture_id))

    total_lectures = len(lecture_keys)

    # -------------------------------------------------
    # 4️⃣ Build table
    # -------------------------------------------------
    table = {}

    for sid, info in students.items():
        attendance_list = []

        for date, lecture_id in lecture_keys:
            students_present = subject_data[date][lecture_id]

            if sid in students_present:
                attendance_list.append("Present")
            else:
                attendance_list.append("Absent")

        present = attendance_list.count("Present")
        total = len(attendance_list)
        percentage = round((present / total) * 100, 2) if total > 0 else 0
        absent = total - present

        # ---- STATUS LOGIC (EXACT SAME AS ADMIN) ----
        if total == 0:
            status = "No Data"
        elif percentage >= 75:
            status = "Regular"
        elif percentage >= 50:
            status = "At Risk"
        else:
            status = "Critical"

        table[sid] = {
            "name": info.get("name", "Unknown"),
            "present": present,
            "absent": absent,
            "total": total,
            "percentage": percentage,
            "status": status          # ✅ THIS WAS MISSING
        }


    return render_template(
        "view_student_data.html",
        table=table,
        course=course,
        class_key=class_key,
        subject=subject,
        total_lectures = total_lectures
    )

import uuid
from datetime import datetime

# ----------------- Teacher Start Attendance -----------------
@app.route('/teacher/start_attendance')
def teacher_start_attendance():   # <-- function name updated
    if 'teacher' not in session:
        return redirect(url_for('teacher_login'))

    course = session.get('course')
    class_key = session.get('class_key')
    subject = session.get('subject')

    # Generate a unique session ID
    session_id = str(uuid.uuid4())[:8]

    # Store attendance session in Firebase
    attendance_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance/current_session")
    attendance_ref.set({
        'active': True,
        'session_id': session_id,
        'timestamp': db.SERVER_TIMESTAMP
    })

    return render_template(
        'start_attendance.html',
        course=course,
        class_key=class_key,
        subject=subject,
        session_id=session_id
    )

@app.route('/teacher/stop_attendance/<subject>')
def teacher_stop_attendance(subject):  # <-- function name updated
    if 'teacher' not in session:
        return redirect(url_for('teacher_login'))

    course = session.get('course')
    class_key = session.get('class_key')

    # Mark the attendance session as inactive
    attendance_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance/current_session")
    attendance_ref.update({'active': False})

    return redirect(url_for('teacher_dashboard'))

# ----------------- Portion Completion (Updated) -----------------yes
@app.route("/teacher/portion_completion/<course>/<class_key>/<subject>", methods=["GET", "POST"])
def portion_completion(course, class_key, subject):
    if "teacher" not in session:
        return redirect(url_for("teacher_login"))

    subjects_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects")
    subjects_data = subjects_ref.get() or {}
    subjects = list(subjects_data.keys())

    portion_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/portion_completed")
    current_portion = portion_ref.get() or []

    if request.method == "POST":
        chapter = request.form.get("chapter", "").strip()
        details = request.form.get("details", "").strip()
        selected_subject = request.form.get("subject", subject)

        if chapter and details:
            new_entry = {
                "chapter": chapter,
                "details": details,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            # Fetch existing list or create new
            existing_entries = db.reference(f"courses/{course}/classes/{class_key}/subjects/{selected_subject}/portion_completed").get() or []
            existing_entries.append(new_entry)
            # Save updated list back to Firebase
            db.reference(f"courses/{course}/classes/{class_key}/subjects/{selected_subject}/portion_completed").set(existing_entries)

            flash(f"Portion updated successfully for {selected_subject}!", "success")
            return redirect(url_for("portion_completion", course=course, class_key=class_key, subject=selected_subject))

    return render_template(
        "teacher_portion_completion.html",
        course=course,
        class_key=class_key,
        subject=subject,
        subjects=subjects,
        current_portion=current_portion,
        firebase_url="https://face-recognation-attendance-default-rtdb.asia-southeast1.firebasedatabase.app/"
    )

@app.route("/teacher/new_announcement", methods=["GET", "POST"])
def teacher_new_announcement():
    if "teacher_name" not in session:
        flash("Please login as teacher to post announcements.", "danger")
        return redirect(url_for("teacher_login"))

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        uploader_role = "Teacher"
        uploader_name = session["teacher_name"]

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Push to the centralized notices node using pyrebase
        db.child("notices").push({
            "title": title,
            "body": body,
            "uploader_role": uploader_role,
            "uploader_name": uploader_name,
            "timestamp": timestamp
        })

        flash("Notice uploaded successfully!", "success")
        return redirect(url_for("teacher_dashboard"))

    return render_template("upload_notice.html")

# ----------------- Delete Announcement -----------------
@app.route("/delete_announcement/<notice_id>", methods=["POST"])
def delete_announcement(notice_id):
    # Check if logged in as Admin or Teacher
    if "admin_logged_in" in session or "teacher_name" in session:
        try:
            db.child("notices").child(notice_id).remove()
            flash("Announcement deleted successfully!", "success")
        except:
            flash("Failed to delete announcement.", "danger")
    else:
        flash("Unauthorized action.", "danger")

    # Redirect back
    if "admin_logged_in" in session:
        return redirect(url_for("admin_dashboard"))
    elif "teacher_name" in session:
        return redirect(url_for("teacher_dashboard"))
    else:
        return redirect(url_for("home"))

import time, random, string
from flask import request, jsonify, session, flash, redirect, url_for

def generate_random_code(n=6):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(random.choices(alphabet, k=n))

def get_live_session_ref(admin_id, course, class_key, subject):
    return db.reference(f"live_sessions/{admin_id}/{course}/{class_key}/{subject}")


@app.route("/generate_class_code", methods=["POST"])
def generate_class_code():
    if not session.get("logged_in") or session.get("role") != "teacher":
        return jsonify({"ok": False, "msg": "Not authorized"}), 401

    teacher_email = session.get("email")
    teachers = db.reference("teachers").get() or {}
    teacher_data = next((v for k, v in teachers.items() if v.get("email") == teacher_email), None)
    if not teacher_data:
        return jsonify({"ok": False, "msg": "Teacher not found"}), 404

    course  = request.json.get("course")  or teacher_data.get("course")
    class_key = request.json.get("class_key") or teacher_data.get("class_key")
    subject = request.json.get("subject") or teacher_data.get("subject")
    admin_id = teacher_data.get("admin_id")          # ✅ VERY IMPORTANT
    teacher_id = teacher_data.get("id") or teacher_data.get("email")

    # generate code + times
    code = generate_random_code(6)
    now = int(tm.time())
    expires_at = now + (10 * 60)

    live_ref = get_live_session_ref(admin_id, course, class_key, subject)  # ✅ FIXED

    session_id = str(int(tm.time()))  # ✅ UNIQUE PER LECTURE
    
    live_ref.set({
        "session_id": session_id,
        "class_code": code,
        "teacher_id": teacher_id,
        "teacher_name": teacher_data.get("name"),
        "start_time": now,
        "expires_at": expires_at,
        "status": "active"
    })

    session["active_subject"] = subject
    session["admin_id"] = admin_id
    session["last_class_code"] = code

    return jsonify({
        "ok": True,
        "code": code,
        "expires_at": expires_at,
        "course": course,
        "class_key": class_key,
        "subject": subject
    })

@app.route("/extend_session", methods=["POST"])
def extend_session():
    data = request.get_json()
    course = data["course"]
    class_key = data["class_key"]
    subject = data["subject"]

    teacher_email = session.get("email")
    teachers = db.reference("teachers").get() or {}
    teacher_data = next((v for k, v in teachers.items() if v.get("email") == teacher_email), None)

    admin_id = teacher_data["admin_id"]

    live_ref = get_live_session_ref(admin_id, course, class_key, subject)
    live_data = live_ref.get()

    if not live_data:
        return jsonify({"ok": False}), 404

    new_expiry = live_data["expires_at"] + 300
    live_ref.update({"expires_at": new_expiry})

    return jsonify({"ok": True, "expires_at": new_expiry})

@app.route("/end_session", methods=["POST"])
def end_session():
    data = request.get_json()
    course = data["course"]
    class_key = data["class_key"]
    subject = data["subject"]

    teacher_email = session.get("email")
    teachers = db.reference("teachers").get() or {}
    teacher_data = next((v for k, v in teachers.items() if v.get("email") == teacher_email), None)

    admin_id = teacher_data["admin_id"]

    live_ref = get_live_session_ref(admin_id, course, class_key, subject)
    live_ref.delete()

    return jsonify({"ok": True})

from datetime import datetime, timedelta

@app.route("/teacher_schedule")
def teacher_schedule():

    if not session.get("logged_in") or session.get("role") != "teacher":
        return redirect(url_for("index"))

    teacher_id = session.get("teacher_id")
    admin_id = session.get("admin_id")

    # 🔹 FETCH TEACHER DATA
    teacher_ref = db.reference(f"teachers/{teacher_id}")
    teacher_data = teacher_ref.get() or {}

    teacher_subject = teacher_data.get("subject")

    schedule_ref = db.reference(f"admins/{admin_id}/schedule")
    raw_schedule = schedule_ref.get() or {}

    organized_schedule = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": []
    }

    for lec_id, lec in raw_schedule.items():
        if (
            lec.get("teacher_id") == teacher_id and
            lec.get("subject") == teacher_subject
        ):
            day = lec.get("day")

            # ✅ ADD THESE LINES IMMEDIATELY BELOW
            day_map = {
                "Mon": "Monday",
                "Tue": "Tuesday",
                "Wed": "Wednesday",
                "Thu": "Thursday",
                "Fri": "Friday",
                "Sat": "Saturday",
                "Monday": "Monday",
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
                "Friday": "Friday",
                "Saturday": "Saturday"
            }

            day = day_map.get(day, day)

            if day in organized_schedule:
                organized_schedule[day].append(lec)

    # 🕒 COLLECT DYNAMIC TIME SLOTS FROM ADMIN DATA
    time_slots_set = set()

    for day_lectures in organized_schedule.values():
        for lec in day_lectures:
            slot = f"{lec['start_time']}-{lec['end_time']}"
            time_slots_set.add(slot)

    # 🔢 SORT TIME SLOTS BY START TIME
    def time_sort_key(slot):
        start = slot.split("-")[0]
        return datetime.strptime(start, "%H:%M")

    time_slots = sorted(list(time_slots_set), key=time_sort_key)

    # 🔔 FETCH TEACHER REMINDERS
    reminders = db.reference(
        f"teachers/{teacher_id}/reminders"
    ).get() or {}

    # 📅 CURRENT WEEK
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    week_label = f"{start_of_week.strftime('%b %d')} – {end_of_week.strftime('%d, %Y')}"

    today_date = today.date()

    week_days = []
    for i in range(6):  # Mon–Sat
        d = start_of_week + timedelta(days=i)
        week_days.append({
            "short": d.strftime("%a"),        # Mon
            "full_name": d.strftime("%A"),    # Monday
            "date": d.strftime("%d"),
            "is_today": d.date() == today_date
        })

    print("TODAY:", today)
    print("START WEEK:", start_of_week)

    today_label = today.strftime("%b %d, %Y")

    return render_template(
        "teacher_schedule.html",
        weekly=organized_schedule,   # ✅ IMPORTANT
        reminders=reminders,
        week_label=week_label,
        week_days=week_days,
        today_label=today_label,
        teacher_subject=teacher_subject,
        time_slots=time_slots
    )


@app.route("/teacher_add_reminder", methods=["POST"])
def teacher_add_reminder():

    if not session.get("logged_in") or session.get("role") != "teacher":
        return redirect(url_for("index"))

    teacher_id = session.get("teacher_id")

    text = request.form.get("text")
    datetime = request.form.get("datetime")

    db.reference(f"teachers/{teacher_id}/reminders").push({
        "text": text,
        "datetime": datetime
    })

    return redirect(url_for("teacher_schedule"))

@app.route("/teacher_notice")
def teacher_notice():
    if "teacher_id" not in session:
        return redirect(url_for("home"))

    teacher_name = session.get("name", "Teacher")
    course = session["course"]
    class_key = session["class_key"]

    # GET FILTER PARAMS
    search = request.args.get("search", "").lower().strip()
    category = request.args.get("category", "all")

    # -----------------------------
    # ADMIN NOTICES (FILTER BY ADMIN ID)
    # -----------------------------
    admin_id = session.get("admin_id")      # <-- Make sure this is added

    admin_ref = db.reference("notices").get() or {}

    admin_notices = []
    for v in admin_ref.values():
        if not isinstance(v, dict):   # skip corrupted entries
            print("Skipping invalid admin notice:", v)
            continue

        if v.get("audience") in ("teachers", "both") and v.get("admin_id") == admin_id:
            admin_notices.append(v)


    # -----------------------------
    # TEACHER NOTICES (Class)
    # -----------------------------
    teacher_ref = db.reference(f"courses/{course}/classes/{class_key}/notices").get() or {}
    teacher_notices = [
        { "id": key, **value }
        for key, value in teacher_ref.items()
    ]

    # TEACHER-UPLOADED ONLY  (right side list)
    # -----------------------------
    my_notices = [
        { "id": key, **value }
        for key, value in teacher_ref.items()
        if value.get("uploader_role") == "teacher"
    ]

    notices = admin_notices + teacher_notices

    # -----------------------------
    # 🔍 SEARCH FILTER
    # -----------------------------
    if search:
        notices = [
            n for n in notices
            if search in n.get("title", "").lower()
            or search in n.get("body", "").lower()
        ]

    # -----------------------------
    # 🎯 CATEGORY FILTER
    # -----------------------------
    if category != "all":
        notices = [n for n in notices if n.get("category") == category]

    # SORT NOTICES
    notices.sort(key=lambda x: parse_ts(x.get("timestamp", "")), reverse=True)


    return render_template(
        "teacher_notice.html",
        teacher_name=teacher_name,
        notices=notices,
        admin_notices=admin_notices,      # 🟢 ADD THIS
        teacher_notices=teacher_notices,  # 🟢 already present
        my_notices=my_notices             # 🟢 optional if needed
    )

@app.route("/delete_teacher_notice/<notice_id>", methods=["POST"])
def delete_teacher_notice(notice_id):
    if "teacher_id" not in session:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("home"))

    course = session["course"]
    class_key = session["class_key"]

    ref = db.reference(f"courses/{course}/classes/{class_key}/notices/{notice_id}")

    # Check if notice exists before deleting
    notice = ref.get()
    if not notice:
        flash("Notice not found!", "danger")
        return redirect(url_for("teacher_notice"))

    # Ensure teacher can delete **only their own notices**
    if notice.get("uploader_role") != "teacher":
        flash("❌ You can only delete notices you posted.", "warning")
        return redirect(url_for("teacher_notice"))

    ref.delete()

    flash("🗑️ Notice deleted successfully.", "success")
    return redirect(url_for("teacher_notice"))

@app.route("/upload_notice_teacher", methods=["POST"])
def upload_notice_teacher():
    if "teacher_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("home"))

    teacher_id = session["teacher_id"]
    teacher_name = session.get("teacher_name", "Teacher")

    # Teacher belongs to one course & class
    course = session.get("course")
    class_key = session.get("class_key")

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    notice_data = {
        "title": title,
        "body": body,
        "uploader_role": "teacher",
        "uploader_name": teacher_name,
        "teacher_id": teacher_id,
        "course": course,
        "class_key": class_key,
        "audience": "students",
        "status": "published",
        "timestamp": timestamp,
        "posted_by": session.get("name", "Teacher")
    }

    # Save teacher notice in their own class location
    db.reference(f"courses/{course}/classes/{class_key}/notices").push(notice_data)

    flash("Notice posted successfully!", "success")
    return redirect(url_for("teacher_notice"))

from datetime import datetime

def parse_ts(ts):
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M")
    except:
        return datetime.min


from datetime import date
from flask import request, render_template, session

@app.route("/teacher_portion_completion", methods=["GET", "POST"])
def teacher_portion_completion():

    # Get teacher session
    teacher = {
        "admin_id": session.get("admin_id"),
        "course": session.get("course"),
        "class_key": session.get("class_key"),
        "subject": session.get("subject")
    }

    admin_id = teacher["admin_id"]
    course = teacher["course"]
    class_key = teacher["class_key"]
    subject = teacher["subject"]

    # Firebase base path
    base_path = f"admins/{admin_id}/courses/{course}/classes/{class_key}/subjects/{subject}"
    ref = db.reference(base_path)

    # -------- SAVE TEACHER NAME IN FIREBASE (so admin can see it) --------
    teacher_name = session.get("teacher_name")
    if teacher_name:
        ref.child("teacher").set(teacher_name)

    # Load portion entries
    portion_entries = ref.child("portion_completed").get() or []

    # Load total chapters
    total_chapters = ref.child("total_chapters").get()
    # Normalize invalid values
    if not isinstance(total_chapters, int) or total_chapters <= 0:
        total_chapters = None

    # Load completed chapters
    completed_chapters = ref.child("completed_chapters").get() or 0

    message = None

    # -------------------------------------------------------
    # 1️⃣ TEACHER SETS or UPDATES TOTAL CHAPTERS
    # -------------------------------------------------------
    if "total_chapters" in request.form:

        new_total = int(request.form.get("total_chapters"))
        ref.child("total_chapters").set(new_total)

        total_chapters = new_total          # update local
        message = "Total chapters updated successfully!"

    # -------------------------------------------------------
    # 2️⃣ TEACHER ENTERS NEW 'COMPLETED CHAPTERS' VALUE
    # -------------------------------------------------------
    elif "completed_chapters" in request.form:

        completed_chapters = int(request.form.get("completed_chapters"))
        ref.child("completed_chapters").set(completed_chapters)

        message = "Completed chapters updated!"

    # -------------------------------------------------------
    # 3️⃣ TEACHER ADDS A NEW PORTION ENTRY
    # -------------------------------------------------------
    elif "chapter" in request.form:

        chapter = request.form.get("chapter")
        details = request.form.get("details")

        new_entry = {
            "chapter": chapter,
            "details": details,
            "timestamp": datetime.now().strftime("%b %d, %Y – %I:%M %p")
        }

        portion_entries.append(new_entry)
        ref.child("portion_completed").set(portion_entries)

        message = "Portion updated successfully!"

    # -------------------------------------------------------
    # SORT previous updates
    # -------------------------------------------------------
    try:
        previous_updates = sorted(
            portion_entries,
            key=lambda x: datetime.strptime(x["timestamp"], "%b %d, %Y – %I:%M %p"),
            reverse=True
        )
    except:
        previous_updates = portion_entries

    # -------------------------------------------------------
    # AUTO-CALCULATE PROGRESS %
    # -------------------------------------------------------
    completed_chapters = len(portion_entries)

    # Save auto-count for admin use
    ref.child("completed_chapters").set(completed_chapters)

    if total_chapters and completed_chapters > 0:
        completion_percent = round((completed_chapters / total_chapters) * 100)
    else:
        completion_percent = 0

    # -------------------------------------------------------
    return render_template(
        "teacher_portion_completion.html",
        subject=subject,
        subject_code=course,
        class_name=class_key,
        message=message,
        completion_percent=completion_percent,
        current_date=date.today().strftime("%B %d, %Y"),
        previous_updates=previous_updates,
        total_chapters=total_chapters,
        completed_chapters=completed_chapters
    )

# ----------------- Teacher Logout -----------------
@app.route("/teacher/logout")
def teacher_logout():
    for key in ["teacher", "course", "class_key", "subject"]:
        session.pop(key, None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("index"))

# ----------------- Teacher View & Update Attendance (Unified) -----------------
@app.route('/teacher/view_attendance/<course>/<subject>', methods=['GET'])
def teacher_view_attendance(course, subject):

    if 'teacher' not in session:
        return redirect(url_for('teacher_login'))

    admin_id = session.get("admin_id")
    class_key = session.get("class_key")
    subject = session.get("subject")   # ✅ SINGLE SOURCE OF TRUTH

    # ===============================
    # FETCH ATTENDANCE DATA
    # ===============================
    attendance_ref = db.reference(
        f"attendance/{admin_id}/{course}/{class_key}/{subject}"
    )
    attendance_data = attendance_ref.get() or {}

    # ===============================
    # GLOBAL TOTAL LECTURES (FOR SUMMARY ONLY)
    # ===============================
    global_total_lectures = 0
    for date, lecture_instances in attendance_data.items():
        global_total_lectures += len(lecture_instances)

    # ===============================
    # FETCH STUDENTS
    # ===============================
    students_ref = db.reference(
        f"admins/{admin_id}/courses/{course}/classes/{class_key}/students"
    )
    students = students_ref.get() or {}

    # ===============================
    # BUILD STUDENT STATS
    # ===============================
    table_data = []
    total_percentage = 0
    counted_students = 0

    for sid, info in students.items():
        present = 0
        total_lectures = 0
        last_seen = "N/A"

        for date, lecture_instances in attendance_data.items():
            for lecture_id, student_map in lecture_instances.items():
                total_lectures += 1     # ✅ count lecture for THIS student
                if sid in student_map:
                    present += 1
                    last_seen = date

        absent = total_lectures - present
        percentage = round(
            (present / total_lectures) * 100, 2
        ) if total_lectures else 0

        if total_lectures == 0:
            status = "No Data"
        elif percentage >= 75:
            status = "Regular"
        elif percentage >= 50:
            status = "At Risk"
        else:
            status = "Critical"

        if total_lectures > 0:
            total_percentage += percentage
            counted_students += 1

        table_data.append({
            "roll": info.get("roll_no", sid),
            "name": info.get("name", "Unknown"),
            "present": present,
            "absent": absent,
            "total": total_lectures,
            "percentage": percentage,
            "last_seen": last_seen,
            "status": status
        })

    avg_attendance = round(
        total_percentage / counted_students, 2
    ) if counted_students else 0

    # ===============================
    # RENDER PAGE
    # ===============================
    return render_template(
        "teacher_view_attendance.html",
        course=course,
        class_key=class_key,
        subject=subject,
        table_data=table_data,
        total_lectures=global_total_lectures,
        avg_attendance=avg_attendance
    )

# ----------------- Teacher Export Attendance CSV -----------------
@app.route('/teacher/export_attendance/<course>/<subject>')
def teacher_export_attendance(course, subject):
    if 'teacher' not in session:
        return redirect(url_for('teacher_login'))

    class_key = session.get('class_key')

    # Get attendance records and students
    attendance_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance")
    attendance_data = attendance_ref.get() or {}
    students_ref = db.reference(f"courses/{course}/classes/{class_key}/students")
    students = students_ref.get() or {}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ["Student ID", "Student Name"] + sorted(attendance_data.keys())
    writer.writerow(header)

    # Data rows
    for student_id, student_info in students.items():
        row = [student_id, student_info.get("name", "")]
        for date in sorted(attendance_data.keys()):
            row.append(attendance_data.get(date, {}).get(student_id, "Absent"))
        writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{course}_{subject}_attendance.csv"
    )

# ----------------- Upload Notice -----------------
@app.route("/upload_notice", methods=["GET", "POST"])
def upload_notice():

    # Correct login check
    if "admin_logged_in" not in session and "teacher_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")

        uploader_name = session.get("name") or session.get("teacher_name")
        uploader_role = "Admin" if "admin_logged_in" in session else "Teacher"

        course_code = session.get("course")

        # Save
        if uploader_role == "Admin":
            notice_ref = db.reference("notices")
        else:
            notice_ref = db.reference(f"courses/{course_code}/notices")

        notice_ref.push({
            "title": title,
            "body": body,
            "uploader_name": uploader_name,
            "uploader_role": uploader_role,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash("Notice posted successfully!", "success")
        return redirect(url_for("upload_notice"))

    return render_template("upload_notice.html")

@app.route("/create_notice", methods=["POST"])
def create_notice():
    # Validate login
    if "admin_name" in session:
        uploader_name = session["admin_name"]
        uploader_role = "Admin"
    elif "teacher_name" in session:
        uploader_name = session["teacher_name"]
        uploader_role = "Teacher"
    else:
        flash("You must be logged in as admin or teacher to post notices.", "danger")
        return redirect(url_for("home"))

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    course_code = session.get("course")

    if not title or not body:
        flash("Both title and message are required.", "danger")
        return redirect(url_for("upload_notice"))

    notice_ref = db.reference(f"courses/{course_code}/notices")
    notice_ref.push({
        "title": title,
        "body": body,
        "uploader_name": uploader_name,
        "uploader_role": uploader_role,
        "timestamp": datetime.now().isoformat()
    })

    flash("Notice uploaded successfully.", "success")
    return redirect(url_for("upload_notice"))



import csv, random, string
from flask import request, flash, redirect, url_for, render_template

# ----------------- Student Login -----------------
@app.route("/student_login", methods=["POST"])
def student_login():
    student_id = (request.form.get("student_id") or "").strip()
    password = (request.form.get("student_password") or "").strip()

    if not student_id or not password:
        flash("Please enter both Roll Number and Password.", "danger")
        return redirect(url_for("home"))

    courses_data = db.reference("courses").get() or {}
    student_data, course_code, class_key = None, None, None

    for c_key, c_val in courses_data.items():
        for cls_key, cls_val in c_val.get("classes", {}).items():
            students = cls_val.get("students", {})
            if student_id in students and students[student_id].get("password") == password:
                student_data = students[student_id]
                course_code, class_key = c_key, cls_key
                break
        if student_data:
            break

    if student_data:
        # Save student session
        session["student_id"] = student_id
        session["course"] = course_code
        session["class"] = class_key
        session["student_name"] = student_data.get("name", student_id)

        if not student_data.get("face_encodings"):
            flash("Please create your profile first!", "warning")
            return redirect(url_for("student_profile"))

        return redirect(url_for("student_dashboard"))
    else:
        flash("Invalid Roll Number or Password.", "danger")
        return redirect(url_for("home"))

# ----------------- Student Profile / Face Registration -----------------
@app.route("/student_profile", methods=["GET", "POST"])
def student_profile():
    # Ensure logged in
    if not session.get("logged_in") or session.get("role") != "student":
        flash("Please login first!", "warning")
        return redirect(url_for("index"))

    student_uid = session.get("student_uid")
    if not student_uid:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("index"))

    # Fetch student full record from students_main
    student_data = db.reference("students_main").child(student_uid).get() or {}

    # ---- FETCH FACE REGISTRATION STATUS ----
    face_meta = student_data.get("face_meta", {})
    face_registered = face_meta.get("face_registered", False)
    last_updated_ts = face_meta.get("last_updated")

    # Convert timestamp to readable date
    last_updated_str = None
    if last_updated_ts:
        last_updated_str = datetime.fromtimestamp(last_updated_ts).strftime("%b %d, %Y")

    student_id = student_data.get("student_id")
    course_code = student_data.get("course")
    class_key = student_data.get("class_key")
    admin_id = student_data.get("admin_id")
    student_name = student_data.get("name")
    institute_name = student_data.get("institute_name")

    # Fetch subjects for attendance
    subjects_data = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{class_key}/subjects"
    ).get() or {}

    subjects = list(subjects_data.keys())

    # Attendance summary
    attendance_summary, total_classes_all, total_present_all = [], 0, 0
    for subject, sub_data in subjects_data.items():
        attendance = sub_data.get("attendance", {}) or {}
        total_classes = len(attendance)
        present_count = sum(1 for rec in attendance.values() if rec.get(student_id) == "Present")
        percent = round((present_count / total_classes) * 100, 2) if total_classes else 0

        attendance_summary.append({
            "subject": subject,
            "attended": present_count,
            "total": total_classes,
            "percent": percent
        })

        total_classes_all += total_classes
        total_present_all += present_count

    overall_percentage = (
        round((total_present_all / total_classes_all) * 100, 2)
        if total_classes_all else 0
    )

    # Face registration handling
    update_mode = request.args.get("update", "false").lower() == "true"

    if request.method == "POST":
        images = request.form.getlist("captured_images[]")

        if len(images) < 3:
            flash("Capture at least 3 images.", "warning")
            return redirect(url_for("student_profile", update=update_mode))

        face_encodings_list = []
        for img in images:
            try:
                img_bytes = base64.b64decode(img.split(",")[1])
                frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                encs = face_recognition.face_encodings(frame)
                if encs:
                    face_encodings_list.append(encs[0].tolist())
            except:
                pass

        if not face_encodings_list:
            flash("No face detected.", "danger")
            return redirect(url_for("student_profile", update=update_mode))

        # Save under THIS student
        db.reference("students_main").child(student_uid).update({
            "face_encodings": face_encodings_list
        })

        flash("Profile Updated!" if update_mode else "Face Registered!", "success")
        return redirect(url_for("student_profile"))

    return render_template(
        "student_profile.html",
        student_name=student_name,
        institute_name=institute_name,
        student_id=student_id,
        subjects=subjects,
        attendance_summary=attendance_summary,
        overall_percentage=overall_percentage,
        update_mode=update_mode,
        face_registered=face_registered,
        last_updated_str=last_updated_str
    )

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if not value:
        return ""
    return datetime.fromtimestamp(value).strftime("%b %d, %Y %I:%M %p")

import base64, io, os, time
from flask import request, jsonify, session, redirect, url_for, flash
import numpy as np

@app.route("/register_face", methods=["POST"])
def register_face():
    # ensure logged-in student
    if not session.get("logged_in") or session.get("role") != "student":
        return jsonify({"ok": False, "msg": "Not logged in"}), 401

    student_id = str(session.get("student_id"))
    admin_id = session.get("admin_id")

    data = request.get_json() or {}
    images = data.get("images", [])   # expect list of base64 dataurls

    if not images or not isinstance(images, list):
        return jsonify({"ok": False, "msg": "No images provided"}), 400

    encodings = []
    thumbs_dir = os.path.join("static", "face_thumbs")
    os.makedirs(thumbs_dir, exist_ok=True)

    for i, dataurl in enumerate(images):
        try:
            header, b64 = dataurl.split(",", 1)
        except Exception:
            return jsonify({"ok": False, "msg": f"Image {i+1} invalid format"}), 400

        img_bytes = base64.b64decode(b64)
        # use cv2 or PIL to load - we use face_recognition load from bytes
        img = face_recognition.load_image_file(io.BytesIO(img_bytes))
        face_locations = face_recognition.face_locations(img, model="hog")
        if len(face_locations) == 0:
            return jsonify({"ok": False, "msg": f"No face found in image {i+1}. Please recapture."}), 400

        enc = face_recognition.face_encodings(img, known_face_locations=face_locations)
        if not enc:
            return jsonify({"ok": False, "msg": f"Failed to get encoding for image {i+1}."}), 400

        encodings.append(enc[0])

        # save a small thumbnail for UI (optional)
        im = Image.open(io.BytesIO(img_bytes))
        im.thumbnail((200,200))
        thumb_path = os.path.join(thumbs_dir, f"{student_id}_thumb_{i+1}.jpg")
        im.save(thumb_path, format="JPEG", quality=70)

    if not encodings:
        return jsonify({"ok": False, "msg": "No valid face encodings."}), 400

    # Save encodings array (Nx128)
    enc_array = np.stack(encodings)  # shape (N,128)
    enc_path = os.path.join("student_encodings", f"{student_id}.npy")
    os.makedirs(os.path.dirname(enc_path), exist_ok=True)
    np.save(enc_path, enc_array)

    # Update Firebase metadata (optional but recommended)
    try:
        meta = {
            "face_registered": True,
            "enc_count": enc_array.shape[0],
            "last_updated": int(time.time())
        }
        student_node_key = session.get("student_uid")

        if not student_node_key:
            return jsonify({"ok": False, "msg": "Student record not found in Firebase"}), 400

        db.reference(f"students_main/{student_node_key}/face_meta").update(meta)

    except Exception as e:
        # not fatal, but log
        print("Firebase update failed:", e)

    return jsonify({"ok": True, "msg": "Face registered", "encodings": enc_array.shape[0]})

def find_student_node(admin_id, student_id):
    ref = db.reference(f"students_main")
    all_students = ref.get()

    # find the node where student_id matches
    for key, data in all_students.items():
        if data.get("student_id") == str(student_id) and data.get("admin_id") == admin_id:
            return key   # this is "-Of9ghn6FHAoEvyUV5Fo"

    return None

# ----------------- Student Dashboard -----------------
@app.route("/student_dashboard")
def student_dashboard():

    # ---------- AUTH CHECK ----------
    if not session.get("logged_in") or session.get("role") != "student":
        flash("Please login as a student first!", "warning")
        return redirect(url_for("index"))

    student_id = session.get("student_id")
    student_uid = session.get("student_uid")
    if not student_uid:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("index"))

    # ---------- FETCH STUDENT RECORD ----------
    student_data = db.reference("students_main").child(student_uid).get() or {}
    if not student_data:
        flash("Student record not found!", "danger")
        return redirect(url_for("index"))

    student_id      = student_data.get("student_id")
    student_name    = student_data.get("name")
    institute_name  = student_data.get("institute_name")
    course_code     = student_data.get("course")
    class_key       = student_data.get("class_key")
    admin_id        = student_data.get("admin_id")

    # ---------- SUBJECTS ----------
    subjects_path = f"admins/{admin_id}/courses/{course_code}/classes/{class_key}/subjects"
    subjects_data = db.reference(subjects_path).get() or {}
    subjects = list(subjects_data.keys())

    # ---------- ATTENDANCE CALCULATIONS ----------
    attendance_summary = []
    total_classes_all = 0
    total_present_all = 0

    for subject, sub_data in subjects_data.items():

        attendance = sub_data.get("attendance") or {}
        total_classes = len(attendance)

        present_count = sum(
            1 for record in attendance.values()
            if record.get(student_id) == "Present"
        )

        percent = round((present_count / total_classes) * 100, 2) if total_classes else 0

        attendance_summary.append({
            "subject": subject,
            "attended": present_count,
            "total": total_classes,
            "percent": percent
        })

        total_classes_all += total_classes
        total_present_all += present_count

    overall_percentage = (
        round((total_present_all / total_classes_all) * 100, 2)
        if total_classes_all else 0
    )

    # ---------- ATTENDANCE ALERTS ----------
    attendance_alerts = {
        data["subject"]: f"⚠ {data['subject']}: Attendance low ({data['percent']}%)"
        for data in attendance_summary if data["percent"] < 75
    }

    overall_alert = (
        f"⚠ Overall attendance is low: {overall_percentage}%"
        if overall_percentage < 75 else None
    )

    # ---------- LOAD LATEST NOTICES (reuse exact logic from student_notices) ----------
    from datetime import datetime

    def parse_ts(ts):
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M")
        except:
            return datetime.min

    latest_notices = []

    # 1️⃣ ADMIN NOTICES → only show if audience is students or both
    admin_ref = db.reference("notices").get() or {}

    for uid, notice in admin_ref.items():
        if not isinstance(notice, dict):
            continue
        if notice.get("audience") in ("students", "both"):
            notice["id"] = uid
            latest_notices.append(notice)

    # 2️⃣ TEACHER NOTICES → use correct path that your notices page uses
    teacher_ref = db.reference(
        f"courses/{course_code}/{class_key}/notices"
    ).get() or {}


    for uid, notice in teacher_ref.items():
        if not isinstance(notice, dict):
            continue
        notice["id"] = uid
        latest_notices.append(notice)

    # 3️⃣ SORT newest → oldest
    latest_notices.sort(key=lambda x: parse_ts(x.get("timestamp", "")), reverse=True)

    # 4️⃣ KEEP ONLY THE LATEST TWO
    latest_notices = latest_notices[:2]

    # ---------- SYLLABUS / PORTION COMPLETION ----------
    syllabus_summary = []

    for subject, sub_data in subjects_data.items():

        portion_list = sub_data.get("portion_completed", []) or []
        total_chapters = sub_data.get("total_chapters", None)
        completed_chapters = sub_data.get("completed_chapters", 0)

        # Sort all topics latest → oldest
        sorted_topics = sorted(
            portion_list,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        # Recent 3 updates
        recent_topics = sorted_topics[:3]

        # Percentage calculation
        if total_chapters:
            percent_done = round((completed_chapters / total_chapters) * 100, 2)
        else:
            percent_done = 0

        # Latest topic info
        if sorted_topics:
            last_topic = sorted_topics[0].get("details") or sorted_topics[0].get("chapter")
            last_timestamp = sorted_topics[0].get("timestamp")
        else:
            last_topic = "No updates yet"
            last_timestamp = "N/A"

        # Add everything to list
        syllabus_summary.append({
            "subject": subject,
            "percent": percent_done,
            "completed": completed_chapters,
            "total": total_chapters,
            "last_topic": last_topic,
            "last_updated": last_timestamp,
            "recent_topics": recent_topics,   # NEW
            "all_topics": sorted_topics       # NEW
        })


    # ---------- RENDER ----------
    return render_template(
        "student_dashboard.html",
        student_name=student_name,
        institute_name=institute_name,
        student_id=student_id,
        course_code=course_code,
        class_key=class_key,
        subjects=subjects,
        attendance_summary=attendance_summary,
        overall_percentage=overall_percentage,
        attendance_alerts=attendance_alerts,
        overall_alert=overall_alert,
        syllabus_summary=syllabus_summary,
        latest_notices=latest_notices 
    )

from datetime import datetime, date
from collections import defaultdict

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

@app.route("/student_schedule")
def student_schedule():
    # auth check
    if not session.get("logged_in") or session.get("role") != "student":
        return redirect(url_for("index"))

    student_uid = session.get("student_uid")
    if not student_uid:
        flash("Session expired. Please login again.", "warning")
        return redirect(url_for("index"))

    # Try to get class and admin_id from session or students node
    student_ref = db.reference(f"students_main/{student_uid}")
    student_data = student_ref.get() or {}
    student_class = session.get("class_key") or student_data.get("class_key")
    admin_id = session.get("admin_id") or student_data.get("admin_id")

    # 🔴 FETCH ONLY VALID SUBJECTS FOR THIS STUDENT
    course_code = student_data.get("course")

    subjects_ref = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{student_class}/subjects"
    )
    valid_subjects = subjects_ref.get() or {}

    valid_subject_names = set(valid_subjects.keys())

    if not admin_id:
        # fallback: try find admin by scanning admins (expensive) - optional
        # but better to ensure student record contains admin_id
        flash("Unable to determine institute. Contact admin.", "danger")
        return redirect(url_for("index"))

    # load raw schedule from admin root
    schedule_ref = db.reference(f"admins/{admin_id}/schedule")
    raw_schedule = schedule_ref.get() or {}

    # Build weekly dict: day -> list of lecture dicts
    weekly = {d: [] for d in WEEK_DAYS}

    # 🔥 Fetch valid subjects for THIS student only
    course_code = student_data.get("course")

    subjects_ref = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{student_class}/subjects"
    )
    valid_subjects = subjects_ref.get() or {}
    valid_subject_names = set(valid_subjects.keys())

    # 🔥 Normalize + STRICT filtering (class + subject)
    for lec_id, lec in (raw_schedule.items() if isinstance(raw_schedule, dict) else []):

        if not isinstance(lec, dict):
            continue

        lec_class = lec.get("class")
        lec_subject = lec.get("subject")
        lec_day = lec.get("day")

        # ❌ skip if class does not match
        if lec_class != student_class:
            continue

        # ❌ skip if subject does NOT belong to this student
        if lec_subject not in valid_subject_names:
            continue

        print("STUDENT:", student_uid)
        print("VALID SUBJECTS:", valid_subject_names)
        print("RAW LECTURE SUBJECT:", lec_subject)

        if lec_day in weekly:
            weekly[lec_day].append({
                "id": lec_id,
                "subject": lec_subject,
                "teacher": lec.get("teacher", "Teacher Not Assigned"),
                "start_time": lec.get("start_time", ""),
                "end_time": lec.get("end_time", ""),
                "room": lec.get("room", ""),
                "class": lec_class
            })


    # helper to parse HH:MM -> time object (returns None if invalid)
    def parse_time(tstr):
        if not tstr:
            return None
        try:
            return datetime.strptime(tstr.strip(), "%H:%M").time()
        except ValueError:
            try:
                return datetime.strptime(tstr.strip(), "%I:%M %p").time()
            except Exception:
                return None

    # sort each day's lectures by start_time
    for d, lecs in weekly.items():
        lecs.sort(key=lambda x: (parse_time(x["start_time"]) or time.min))

    # prepare today's lectures and next upcoming
    today_weekday = date.today().strftime("%A")  # e.g. "Monday"
    today_lectures = weekly.get(today_weekday, [])

    now_time = datetime.now().time()
    next_lecture = None
    for lec in today_lectures:
        st = parse_time(lec["start_time"])
        if st and st >= now_time:
            next_lecture = lec
            break

    # render with current_date friendly string
    current_date = date.today().strftime("%A, %d %b %Y")

    return render_template(
        "student_schedule.html",
        current_date=current_date,
        next_lecture=next_lecture,
        today_lectures=today_lectures,
        weekly=weekly,
        student_class=student_class
    )

# ----------------- View Attendance -----------------
@app.route("/view_attendance", methods=["GET"])
def view_attendance():
    if "student_name" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("home"))

    student_name, student_id, course_code, class_key = (
        session["student_name"],
        session["student_id"],
        session["course"],
        session["class"],
    )

    selected_subject = request.args.get("subject")
    subjects_ref = db.reference(f"courses/{course_code}/classes/{class_key}/subjects")
    subjects_data = subjects_ref.get() or {}

    attendance_summary = []
    for subject, sub_data in subjects_data.items():
        if selected_subject and subject != selected_subject:
            continue
        attendance = sub_data.get("attendance", {}) or {}
        total_classes = len(attendance)
        present_count = sum(1 for records in attendance.values() if records.get(student_id) == "Present")
        percent = round((present_count / total_classes) * 100, 2) if total_classes else 0
        attendance_summary.append({"subject": subject, "attended": present_count, "total": total_classes, "percent": percent})

    return render_template("view_attendance.html",
                           student_name=student_name,
                           student_id=student_id,
                           course_code=course_code,
                           class_key=class_key,
                           subjects=list(subjects_data.keys()),
                           attendance_summary=attendance_summary,
                           selected_subject=selected_subject)


# ----------------- Schedule Attendance -----------------
from datetime import datetime

@app.route("/schedule_attendance")
def schedule_attendance():
    # Must be logged in
    if "student_id" not in session:
        return redirect(url_for("home"))

    # Student details
    admin_id = session.get("admin_id")        # The admin who manages them
    student_uid = session.get("student_uid")

    student_ref = db.reference(f"students_main/{student_uid}")
    student_data = student_ref.get() or {}

    student_name = session.get("student_name", "Student")

    # Fetch admin schedule
    schedule_ref = db.reference(f"admins/{admin_id}/schedule")
    raw = schedule_ref.get() or {}

    # Prepare structure
    weekly = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": []
    }
    time_slots = []
    
    today = datetime.now().strftime("%A")
    now_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%A, %d %b %Y")

    today_lectures = []
    sorted_today = []  # For finding next lecture

    student_class = student_data.get("class_key")
    course_code = student_data.get("course")

    subjects_ref = db.reference(
        f"admins/{admin_id}/courses/{course_code}/classes/{student_class}/subjects"
    )
    valid_subjects = subjects_ref.get() or {}
    valid_subject_names = set(valid_subjects.keys())

    # Filter only student's class lectures
    for lec_id, lec in raw.items():

        if not isinstance(lec, dict):
            continue

        lec_class = lec.get("class")
        lec_subject = lec.get("subject")
        lec_day = lec.get("day")

        if lec_class != student_class:
            continue

        if lec_subject not in valid_subject_names:
            continue

        if lec_day in weekly:
            weekly[lec_day].append(lec)

        if lec_day == today:
            today_lectures.append(lec)
            sorted_today.append(lec)

    # -------- Find next upcoming lecture --------
    def to_minutes(t):
        try:
            h, m = map(int, t.split(":"))
            return h * 60 + m
        except:
            return 9999

    now_m = to_minutes(now_time)
    next_lecture = None

    sorted_today.sort(key=lambda x: to_minutes(x["start_time"]))

    for lec in sorted_today:
        if to_minutes(lec["start_time"]) > now_m:
            next_lecture = lec
            break

    # ---- Build DYNAMIC time slots based on admin's timetable ----
    all_times = set()

    for day, lectures in weekly.items():
        for lec in lectures:
            slot = f"{lec['start_time']}-{lec['end_time']}"
            all_times.add(slot)

    # Sort slots by actual time
    def sort_key(slot):
        start = slot.split("-")[0]
        h, m = map(int, start.split(":"))
        return h * 60 + m

    time_slots = sorted(list(all_times), key=sort_key)

    reminders_ref = db.reference(f"students_main/{session.get('student_uid')}/reminders")
    reminders = reminders_ref.get() or {}

    # Render page
    return render_template(
        "schedule_attendance.html",
        student_name=student_name,
        current_date=current_date,
        next_lecture=next_lecture,
        today_lectures=today_lectures,
        weekly=weekly,
        time_slots=time_slots,
        reminders=reminders 
    )

@app.route("/add_reminder", methods=["POST"])
def add_reminder():
    if "student_uid" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("index"))

    student_uid = session["student_uid"]

    title = request.form.get("title")
    description = request.form.get("description", "")
    date = request.form.get("date")
    time = request.form.get("time")

    reminder_data = {
        "title": title,
        "description": description,
        "date": date,
        "time": time
    }

    # Save under each student's reminders
    db.reference(f"students_main/{student_uid}/reminders").push(reminder_data)

    flash("Reminder added successfully!", "success")
    return redirect(url_for("schedule_attendance"))

from flask import jsonify

@app.route("/student/attendance/<course>", methods=["GET", "POST"])
def student_attendance(course):

    # Ensure student logged in
    if not session.get("logged_in") or session.get("role") != "student":
        return redirect(url_for("index"))

    student_id = session.get("student_id")
    admin_id = session.get("admin_id")
    student_name = session.get("name")

    class_key = session.get("class_key")
    # ================= FETCH TODAY'S LECTURES =================

    schedule_ref = db.reference(f"admins/{admin_id}/schedule")
    raw_schedule = schedule_ref.get() or {}

    today = datetime.now().strftime("%A")
    now_time = datetime.now().strftime("%H:%M")

    print("====== TIME DEBUG ======")
    print("SERVER DAY:", today)
    print("SERVER TIME:", now_time)
    print("========================")

    def to_minutes(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m

    now_m = to_minutes(now_time)

    today_lectures = []
    current_lecture = None

    for lec in raw_schedule.values():
        if lec.get("class") != class_key:
            continue

        if lec.get("day") != today:
            continue

        lec_start = to_minutes(lec["start_time"])
        lec_end   = to_minutes(lec["end_time"])

        # ❌ skip lectures that are already over
        if now_m > lec_end:
            continue

        # ✅ detect current lecture
        if lec_start <= now_m <= lec_end:
            current_lecture = lec

        # ✅ only upcoming + current lectures
        today_lectures.append(lec)


        print("LEC DAY:", lec.get("day"))
        print("LEC TIME:", lec.get("start_time"), "-", lec.get("end_time"))
        print("LEC CLASS:", lec.get("class"), "| SESSION CLASS:", class_key)
        print("------")

    # ========== 2️⃣ IF GET — load page ==================
    if request.method == "GET":
        return render_template(
            "student_attendance.html",
            course=course,
            class_key=class_key,
            admin_id=admin_id,
            marked=False,
            today_lectures=today_lectures,
            current_lecture=current_lecture
        )

    # ========== 3️⃣ IF POST — submit attendance ==========

    print("POST ATTENDANCE TRIGGERED")
    # 🔥 RE-FETCH live session on POST (IMPORTANT)
    
    # 🔥 USE VERIFIED SUBJECT FROM SESSION (DO NOT recompute)
    subject = session.get("active_subject")

    print("POST → active_subject:", session.get("active_subject"))

    print("ACTIVE SUBJECT FROM SESSION:", subject)

    if not subject:
        return render_template(
            "student_attendance.html",
            course=course,
            error="Attendance session expired. Please re-enter class code."
        )

    live_ref = db.reference(
        f"live_sessions/{admin_id}/{course}/{class_key}/{subject}"
    )
    live_data = live_ref.get()

    if not live_data:
        return render_template(
            "student_attendance.html",
            course=course,
            error="No active attendance session."
        )

    lecture_id = live_data.get("session_id") or live_data.get("started_at")

    print("STUDENT ID:", student_id)
    print("ADMIN ID:", admin_id)
    print("COURSE:", course)
    print("SUBJECT:", subject)
    print("CLASS KEY:", class_key)

    submitted_code = request.form.get("class_code")
    captured_image = request.form.get("captured_image")

    # 🔴 SAFETY CHECK — ensure session still active
    if not live_data:
        print("ERROR → No live session found")
        return render_template(
            "student_attendance.html",
            course=course,
            error="No active attendance session."
        )

    print("STEP 2 → Attendance POST triggered")
    print("Captured image exists:", bool(captured_image))

    # 3a — verify class code
    if submitted_code != live_data.get("class_code"):
        return render_template(
            "student_attendance.html",
            course=course,
            teacher=live_data.get("teacher_name", "Teacher"),
            error="Incorrect class code!"
        )

    # 3b — verify session expiry
    now = int(_time.time())
    if now > live_data.get("expires_at"):
        return render_template(
            "student_attendance.html",
            course=course,
            subject=subject,
            error="Session expired."
        )

    # 3c — do face recognition
    if not captured_image:
        return render_template(
            "student_attendance.html",
            course=course,
            subject=subject,
            error="No face detected."
        )

    # Decode image
    img_bytes = base64.b64decode(captured_image.split(",")[1])
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    print("STEP 2 → Image decoded:", img is not None)

    # Load student reference encodings
    student_enc_path = f"student_encodings/{student_id}.npy"
    if not os.path.exists(student_enc_path):
        return render_template(
            "student_attendance.html",
            course=course,
            subject=subject,
            error="Student face not registered."
        )

    known_encoding = np.load(student_enc_path)

    # 🔥 CONVERT IMAGE TO RGB (REQUIRED)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 🔥 STEP 1 — DETECT FACE LOCATIONS
    face_locations = face_recognition.face_locations(rgb_img)

    # 🔥 HARD SAFETY CHECK — reject blank / stale frames
    if img is None or img.size == 0:
        return render_template(
            "student_attendance.html",
            course=course,
            subject=subject,
            error="Camera frame invalid. Please face the camera."
        )

    # ❌ MUST HAVE EXACTLY ONE FACE
    if len(face_locations) != 1:
        print("❌ FACE CHECK FAILED →", len(face_locations))
        return (
            render_template(
                "student_attendance.html",
                course=course,
                subject=subject,
                error="Face not clearly visible. Attendance NOT marked."
            ),
            400
        )


    print("STEP 2 → Faces detected:", len(face_locations))

    # 🔥 STEP 2 — EXTRACT ENCODING ONLY IF FACE EXISTS
    encodings = face_recognition.face_encodings(rgb_img, face_locations)
    captured_encoding = encodings[0]


    # Compare
    matches = face_recognition.compare_faces(
        known_encoding,
        captured_encoding,
        tolerance=0.45
    )

    # ❌ FACE DOES NOT MATCH REGISTERED FACE
    if not any(matches):
        print("❌ FACE MISMATCH")
        return (
            render_template(
                "student_attendance.html",
                course=course,
                subject=subject,
                error="Face mismatch. Attendance NOT marked."
            ),
            400
        )


    # ========== 4️⃣ Mark attendance in Firebase ============
    date_today = datetime.now().strftime("%Y-%m-%d")

    attendance_ref = db.reference(
        f"attendance/{admin_id}/{course}/{class_key}/{subject}/{date_today}/{lecture_id}"
    )


   # 🔒 Prevent duplicate attendance for SAME CLASS CODE
    student_attendance_ref = attendance_ref.child(student_id)
    already_marked = student_attendance_ref.get()

    if already_marked:
        return render_template(
            "student_attendance.html",
            course=course,
            subject=subject,
            error="Attendance already marked for this lecture."
        )

    attendance_ref.child(student_id).set({
        "name": student_name,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "class_code": submitted_code
    })

    return render_template(
        "student_attendance.html",
        course=course,
        subject=subject,
        live_data=live_data,
        current_lecture=current_lecture,
        today_lectures=today_lectures,
        teacher=live_data.get("teacher_name", "Teacher") if live_data else "Teacher",
        marked=True,
        marked_time=datetime.now().strftime("%H:%M:%S")
    )

@app.route("/student/attendance")
def student_attendance_redirect():
    print(
        "Redirect Debug:",
        session.get("course"),
        session.get("class_key"),
        session.get("admin_id")
    )

    if not session.get("logged_in") or session.get("role") != "student":
        return redirect(url_for("index"))

    course = session.get("course")

    if not course:
        flash("Course not found in session.", "warning")
        return redirect(url_for("student_dashboard"))

    # 🔒 IMPORTANT: do NOT pass subject
    return redirect(url_for("student_attendance", course=course))

from urllib.parse import unquote

@app.route("/verify_class_code", methods=["POST"])
def verify_class_code():
    data = request.get_json()

    course = data["course"]
    class_key = data["class_key"]
    entered_code = data["class_code"].strip().upper()

    admin_id = session.get("admin_id")

    print("VERIFY DEBUG → admin_id:", admin_id)
    print("VERIFY DEBUG → course:", course)
    print("VERIFY DEBUG → class_key:", class_key)

    if not admin_id:
        return jsonify({
            "ok": False,
            "msg": "Session expired. Please reload the page and try again."
        })

    sessions_ref = db.reference(f"live_sessions/{admin_id}/{course}/{class_key}")
    sessions = sessions_ref.get() or {}

    live_data = None
    actual_subject = None

    if not isinstance(sessions, dict):
        return jsonify({"ok": False, "msg": "No active attendance session."})

    for sub, data in sessions.items():
        if data.get("status") == "active":
            live_data = data
            actual_subject = sub
            break

    if not live_data:
        return jsonify({"ok": False, "msg": "No active attendance session."})

    if str(live_data.get("class_code")).strip().upper() != entered_code:
        return jsonify({"ok": False, "msg": "Invalid class code!"})

    if int(time.time()) > live_data.get("expires_at"):
        return jsonify({"ok": False, "msg": "Attendance session expired."})

    # ✅ SAVE ACTIVE SESSION IN FLASK SESSION (IMPORTANT)

    session["course"] = course
    session["class_key"] = class_key
    session["active_subject"] = actual_subject

    session.permanent = True
    session.modified = True

    print("VERIFY → active_subject:", session.get("active_subject"))

    # ✅ Return complete lecture details
    return jsonify({
        "ok": True,
        "subject": actual_subject,
        "teacher": live_data.get("teacher_name", "Dr. Instructor")
    })

# ----------------- Notices -----------------
@app.route("/notices")
def notices():
    if "student" not in session:
        return redirect(url_for("home"))

    student = session["student"]

    admin_id = student.get("admin_id")
    s_course = student.get("course")
    s_class = student.get("class_key")

    # Load all notices
    all_notices = db.reference("notices").get() or {}

    visible_notices = []

    for nid, n in all_notices.items():

        # must belong to same admin
        if n.get("admin_id") != admin_id:
            continue

        # -------------------------
        # ADMIN NOTICES FOR STUDENTS
        # -------------------------
        if n.get("uploader_role") == "admin":
            if n.get("audience") in ["students", "both"]:
                course_ok = n.get("course") in ["all", s_course]
                class_ok = n.get("class_key") in ["all", s_class]

                if course_ok and class_ok:
                    visible_notices.append(n)

        # -------------------------
        # TEACHER NOTICES
        # -------------------------
        if n.get("uploader_role") == "teacher":
            # Must match student's class & course
            if (n.get("course") == s_course and
                n.get("class_key") == s_class and
                n.get("admin_id") == admin_id):
                visible_notices.append(n)

    # sort newest first
    visible_notices.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # to match your student page (selected first notice)
    selected_notice = visible_notices[0] if visible_notices else None

    return render_template("student_notices.html",
                           notices=visible_notices,
                           selected_notice=selected_notice)

# ----------------- Mark Attendance (Face Recognition) -----------------
@app.route("/student/mark_attendance/<course>/<class_key>/<subject>", methods=["GET", "POST"])
def student_mark_attendance(course, class_key, subject):
    if "student_name" not in session:
        return redirect(url_for("home"))

    student_id, student_name = session["student_id"], session["student_name"]
    attendance_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance/current_session")
    current_session = attendance_ref.get()

    if not current_session or not current_session.get("active", False):
        flash("No active attendance session for this subject.", "warning")
        return redirect(url_for("student_dashboard"))

    session_id = current_session["session_id"]

    if request.method == "GET":
        return render_template("face_recognition.html", course=course, class_key=class_key, subject=subject)

    # Face verification using saved encodings
    images = request.form.getlist("captured_images[]")
    if not images:
        flash("No image captured. Try again.", "danger")
        return redirect(request.url)

    img_data = images[0]
    img_bytes = base64.b64decode(img_data.split(",")[1])
    frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    encodings = face_recognition.face_encodings(frame)
    if not encodings:
        flash("No face detected. Try again.", "danger")
        return redirect(request.url)

    student_ref = db.reference(f"courses/{course}/classes/{class_key}/students/{student_id}")
    student_data = student_ref.get() or {}
    saved_encodings = student_data.get("face_encodings", [])

    if not saved_encodings:
        flash("Face data not found. Please register your profile first.", "warning")
        return redirect(url_for("student_profile"))

    # Compare the captured face with saved encodings
    matches = []
    for saved_encoding in saved_encodings:
        result = face_recognition.compare_faces([np.array(saved_encoding)], encodings[0], tolerance=0.5)
        matches.append(result[0])

    if not any(matches):
        flash("Face mismatch. Attendance not marked.", "danger")
        return redirect(request.url)

    # ✅ Face matched — mark attendance
    today = datetime.now().strftime("%Y-%m-%d")
    attendance_log_ref = db.reference(f"courses/{course}/classes/{class_key}/subjects/{subject}/attendance/{today}")
    attendance_log_ref.update({student_id: "Present"})

    flash("Attendance marked successfully!", "success")
    return redirect(url_for("student_dashboard"))

@app.route("/student_notices")
def student_notices():
    if "student_id" not in session:
        flash("Please login to view notices.", "danger")
        return redirect(url_for("home"))

    from datetime import datetime

    # FUNCTION TO PARSE TIMESTAMP
    def parse_ts(ts):
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M")
        except:
            return datetime.min

    student_name = session["student_name"]
    course = session["course"]
    class_key = session.get("class_key")

    # -----------------------------
    # 1️⃣ ADMIN NOTICES
    # -----------------------------
    admin_ref = db.reference("notices").get() or {}
    admin_notices = []

    for uid, notice in admin_ref.items():

        # ✅ ADD THIS LINE
        if not isinstance(notice, dict):
            continue

        if notice.get("audience") in ("students", "both"):
            notice["id"] = uid
            admin_notices.append(notice)

    # -----------------------------
    # 2️⃣ TEACHER NOTICES
    # -----------------------------
    teacher_ref = db.reference(f"courses/{course}/{class_key}/notices").get() or {}
    teacher_notices = []

    for uid, notice in teacher_ref.items():

        # ✅ ADD THIS LINE
        if not isinstance(notice, dict):
            continue

        notice["id"] = uid
        teacher_notices.append(notice)

    # -----------------------------
    # 3️⃣ COMBINE BOTH
    # -----------------------------
    notices = admin_notices + teacher_notices

    # -----------------------------
    # 4️⃣ SORT NEWEST FIRST
    # -----------------------------
    notices.sort(key=lambda x: parse_ts(x.get("timestamp", "")), reverse=True)

    # -----------------------------
    # 5️⃣ SELECT CURRENT NOTICE
    # -----------------------------
    selected_id = request.args.get("id")

    if selected_id:
        selected_notice = next((n for n in notices if n["id"] == selected_id), None)
    else:
        selected_notice = notices[0] if notices else None

    return render_template(
        "student_notices.html",
        notices=notices,
        selected_notice=selected_notice
    )

@app.route("/student_logout")
def student_logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("index"))

# ----------------- Run App -----------------
if __name__ == "__main__":
    app.run(debug=True)

