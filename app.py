from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, send_from_directory, url_for, jsonify, session, flash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from itsdangerous import URLSafeTimedSerializer
import random
from werkzeug.security import check_password_hash, generate_password_hash
from dateutil.relativedelta import relativedelta
from flask_socketio import SocketIO, emit, join_room, leave_room  
import json
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import time
from threading import Thread
import os
import requests

""" def open_browser_safe():
    try:
        time.sleep(1)  
        webbrowser.open_new("http://127.0.0.1:5000")
    except:
        pass  

# เรียกใช้ใน Thread
Thread(target=open_browser_safe).start() """

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'this_is_a_test_key_for_demo')

RFID_API_KEY = "my_secure_token_only_for_demo"  
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
pcs = {}

OTP_EXPIRE_MINUTES = 3
RESEND_WAIT_SECONDS = 60
MAX_LOGIN_ATTEMPTS = 5    # login ผิดได้ไม่เกิน 5 ครั้งใน 10 นาที
BLOCK_TIME_MINUTES = 10

api_key = os.getenv("MAILJET_API_KEY")
secret_key = os.getenv("MAILJET_SECRET_KEY")

s = URLSafeTimedSerializer(app.secret_key)

DB_PATH = os.environ.get('DB_PATH', '/data')

def get_db_path(db_name):
    return os.path.join(DB_PATH, db_name)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

db = SQLAlchemy(app)

# Model ของตาราง users
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)           # admin, doctor, patient
    is_verified = db.Column(db.Integer, default=0)
    otp = db.Column(db.String(10))
    otp_created_at = db.Column(db.String(50))

    def __repr__(self):
        return f'<User {self.username}>'
    
class AdminOnlyModelView(ModelView):
    def is_accessible(self):
        return 'user_id' in session and session.get("role") == "admin"

    def inaccessible_callback(self, name, **kwargs):
        flash("คุณไม่มีสิทธิ์เข้าถึงหน้านี้", "danger")
        return redirect(url_for("home"))

# สร้างหน้า Flask-Admin
admin = Admin(app, name='User Database Viewer')
admin.add_view(AdminOnlyModelView(User, db.session))

# Database 
def init_users_db():
    conn = sqlite3.connect(get_db_path('users.db'))
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,          -- 'admin', 'doctor', 'patient'
        is_verified INTEGER DEFAULT 0,  -- doctor ต้องรอ admin อนุมัติ, patient และ admin = 1
        otp TEXT,
        otp_created_at TEXT
    )
    ''')
    conn.commit()
    conn.close()

def create_user(username, password, email):
    conn = sqlite3.connect(get_db_path('users.db'))
    c = conn.cursor()
    
    try:
        hashed_password = generate_password_hash(password, method='scrypt')
        c.execute(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            (username, hashed_password, email)
        )
        conn.commit()
        return True
    
    except sqlite3.IntegrityError:
        return False
    
    finally:
        conn.close()

def login_required(role=None):
    """
    - ทุกคนต้องล็อกอิน
    - admin เข้าถึงได้ทุกหน้า
    - role อื่นเข้าถึงได้เฉพาะหน้าที่กำหนด
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash("กรุณาเข้าสู่ระบบก่อน", "warning")
                return redirect(url_for('login'))

            user_role = session.get('role')
            if role and user_role != role and user_role != 'admin':
                flash("คุณไม่มีสิทธิ์เข้าถึงหน้านี้", "danger")
                return redirect(url_for('home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/admin/pending_doctors')
@login_required(role='admin')
def pending_doctors():
    conn = sqlite3.connect(get_db_path('users.db'))
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users WHERE role = 'doctor' AND is_verified = 0")
    doctors = c.fetchall()
    conn.close()
    return render_template('pending_doctors.html', doctors=doctors)

@app.route('/admin/approve_doctor/<int:doctor_id>', methods=['POST'])
@login_required(role='admin')
def approve_doctor(doctor_id):
    conn = sqlite3.connect(get_db_path('users.db'))
    c = conn.cursor()
    c.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()
    flash("อนุมัติบัญชีหมอเรียบร้อยแล้ว", "success")
    return redirect(url_for('pending_doctors'))

@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        email = request.form['email']
        role = request.form['role']  
        is_verified = 1  # admin อนุมัติแล้ว

        with sqlite3.connect(get_db_path('users.db')) as conn:
            conn.execute(
                "INSERT INTO users (username, password, email, role, is_verified) VALUES (?, ?, ?, ?, ?)",
                (username, password, email, role, is_verified)
            )
        return redirect('/admin/dashboard')

    return render_template('admin_add_user.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        # redirect ตาม role
        role = session.get('role')
        if role == 'doctor':
            return redirect(url_for('home'))
        elif role == 'patient':
            return redirect(url_for('home'))
        else:
            return redirect(url_for('home'))

    if 'login_attempts' not in session:
        session['login_attempts'] = 0
        session['last_attempt_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ตรวจสอบเวลาบล็อค
    last_attempt = datetime.strptime(session.get('last_attempt_time'), '%Y-%m-%d %H:%M:%S')
    if datetime.now() > last_attempt + timedelta(minutes=BLOCK_TIME_MINUTES):
        session['login_attempts'] = 0  # reset attempts

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # ตรวจสอบจำนวนครั้งที่ login ผิด
        if session['login_attempts'] >= MAX_LOGIN_ATTEMPTS:
            flash("คุณพยายามเข้าสู่ระบบหลายครั้งเกินไป กรุณารอประมาณ 10 นาที", "danger")
            return render_template('login.html')

        user = get_user(username)
        if user:
            user_id, hashed_password, role, is_verified = user
            if role == 'doctor' and is_verified == 0:
                flash("บัญชีหมอยังรอการอนุมัติจากแอดมิน", "warning")
            elif check_password_hash(hashed_password, password):
                # ล็อกอินสำเร็จ
                session['user'] = user_id
                session['role'] = role
                session['login_attempts'] = 0
                session.permanent = True
                # redirect ตาม role
                if role == 'doctor':
                    return redirect(url_for('home'))
                elif role == 'patient':
                    return redirect(url_for('home'))
                else:
                    return redirect(url_for('home'))
            else:
                session['login_attempts'] += 1
                session['last_attempt_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")
        else:
            session['login_attempts'] += 1
            session['last_attempt_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user', None)
    if request.method == 'POST':
        return jsonify({"message": "Logged out"}), 200
    else:
        flash("ออกจากระบบเรียบร้อยแล้ว", "success")
        return redirect(url_for('login'))

# เช็คว่า username นี้มีใน DB ยัง
def user_exists(username):
    conn = sqlite3.connect(get_db_path('users.db'))
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# ตรวจสอบว่าในฐานข้อมูลมีชื่อผู้ใช้และอีเมลที่รับเข้ามานั้นอยู่แล้วหรือไม่ เพื่อป้องกันการสมัครซ้ำด้วยชื่อผู็ใช้,อีเมลเดียวกัน
def username_or_email_exists(username, email):
    conn = sqlite3.connect(get_db_path('users.db'))
    c = conn.cursor()
    c.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email))
    row = c.fetchone()
    conn.close()
    return row if row else None

# ตรวจสอบว่า username มีค่าแน่ ๆ ก่อนใช้
def get_user(username):
    if not username:
        return None  # ป้องกันกรณี username เป็น None หรือว่าง
    conn = sqlite3.connect(get_db_path('users.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, role, is_verified FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

#สร้าง otp
def generate_otp():
    return str(random.randint(100000, 999999))

# เช็คว่า OTP หมดอายุหรือยัง
def is_expired(created_at):
    return datetime.now() > datetime.fromisoformat(created_at) + timedelta(minutes=OTP_EXPIRE_MINUTES)

#สร้าง OTP และส่ง สำหรับ registerกับ reset password
def send_otp_email(email, username, otp, purpose="register"):
    try:
        if purpose == "register":
            subject = "รหัส OTP สำหรับลงทะเบียน"
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; background-color: #f4f4f4;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4; padding: 20px 0;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; text-align: center;">
                                        <h1 style="color: #ffffff; margin: 0; font-size: 24px;">ยินดีต้อนรับ!</h1>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 30px 25px;">
                                        <p style="color: #333333; font-size: 15px; margin: 0 0 8px 0;">
                                            เรียน <strong>{username}</strong>
                                        </p>
                                        
                                        <p style="color: #555555; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
                                            ขอบคุณที่ลงทะเบียนกับระบบของเรา กรุณาใช้รหัส OTP ด้านล่างเพื่อยืนยันการลงทะเบียน:
                                        </p>
                                        
                                        <!-- OTP Box - ขนาดเล็กลง -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0;">
                                            <tr>
                                                <td align="center" style="background-color: #667eea; padding: 20px; border-radius: 8px;">
                                                    <div style="color: #ffffff !important; font-size: 32px; font-weight: bold; letter-spacing: 6px; font-family: 'Courier New', Courier, monospace; text-align: center;">
                                                        {otp}
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Warning Box -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0;">
                                            <tr>
                                                <td style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 15px; border-radius: 4px;">
                                                    <p style="margin: 0; color: #856404; font-size: 13px;">
                                                        ⏰ <strong>รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที</strong>
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <p style="color: #888888; font-size: 12px; line-height: 1.5; margin: 20px 0 0 0;">
                                            หากคุณไม่ได้ทำการลงทะเบียน กรุณาเพิกเฉยอีเมลนี้
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f8f9fa; padding: 15px 25px; border-top: 1px solid #e9ecef; text-align: center;">
                                        <p style="margin: 0; color: #6c757d; font-size: 11px;">
                                            © 2024 PSU System. All rights reserved.
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            '''
            
        elif purpose == "reset":
            subject = "รหัส OTP สำหรับรีเซ็ตรหัสผ่าน"
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; background-color: #f4f4f4;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4; padding: 20px 0;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background-color: #f5576c; padding: 25px; text-align: center;">
                                        <h1 style="color: #ffffff; margin: 0; font-size: 24px;">รีเซ็ตรหัสผ่าน</h1>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 30px 25px;">
                                        <p style="color: #333333; font-size: 15px; margin: 0 0 8px 0;">
                                            เรียน <strong>{username}</strong>
                                        </p>
                                        
                                        <p style="color: #555555; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
                                            เราได้รับคำขอรีเซ็ตรหัสผ่านของคุณ กรุณาใช้รหัส OTP ด้านล่างเพื่อดำเนินการต่อ:
                                        </p>
                                        
                                        <!-- OTP Box - ขนาดเล็กลง -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0;">
                                            <tr>
                                                <td align="center" style="background-color: #f5576c; padding: 20px; border-radius: 8px;">
                                                    <div style="color: #ffffff !important; font-size: 32px; font-weight: bold; letter-spacing: 6px; font-family: 'Courier New', Courier, monospace; text-align: center;">
                                                        {otp}
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Warning Box -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0;">
                                            <tr>
                                                <td style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 15px; border-radius: 4px;">
                                                    <p style="margin: 0; color: #856404; font-size: 13px;">
                                                        ⏰ <strong>รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที</strong>
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Security Warning -->
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0;">
                                            <tr>
                                                <td style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 12px 15px; border-radius: 4px;">
                                                    <p style="margin: 0; color: #721c24; font-size: 12px; line-height: 1.5;">
                                                        🔒 <strong>เพื่อความปลอดภัย:</strong><br>
                                                        หากคุณไม่ได้ทำการขอรีเซ็ตรหัสผ่าน กรุณาเพิกเฉยอีเมลนี้
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f8f9fa; padding: 15px 25px; border-top: 1px solid #e9ecef; text-align: center;">
                                        <p style="margin: 0; color: #6c757d; font-size: 11px;">
                                            © 2024 PSU System. All rights reserved.
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            '''
        
        else:
            # Default simple version
            subject = "รหัส OTP"
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4; padding: 20px 0;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; padding: 25px; border-radius: 10px;">
                                <tr>
                                    <td>
                                        <h2 style="color: #333333; font-size: 20px;">รหัส OTP ของคุณ</h2>
                                        <p style="color: #555555; font-size: 14px;">เรียน {username},</p>
                                        
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 15px 0;">
                                            <tr>
                                                <td align="center" style="background-color: #4CAF50; padding: 18px; border-radius: 5px;">
                                                    <div style="color: #ffffff !important; font-size: 28px; font-weight: bold; letter-spacing: 5px; font-family: 'Courier New', Courier, monospace;">
                                                        {otp}
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <p style="color: #666666; font-size: 13px;">รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            '''

        api_key = os.getenv("MAILJET_API_KEY")
        secret_key = os.getenv("MAILJET_SECRET_KEY")

        print(f"[DEBUG] Sending OTP to: {email}")

        response = requests.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(api_key, secret_key),
            json={
                "Messages": [{
                    "From": {"Email": "sasivimon.0606@gmail.com", "Name": "ระบบยืนยันตัวตน"},
                    "To": [{"Email": email}],
                    "Subject": subject,
                    "HTMLPart": html_content
                }]
            }
        )
        print(f"[DEBUG] Mailjet response: {response.status_code}")
        return response.status_code == 200

    except Exception as e:
        print(f"[ERROR] ส่งอีเมลล้มเหลว: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/register_login', methods=['GET', 'POST'])
def register_login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()
        role = request.form.get('role')  

        # ตรวจความถูกต้องของข้อมูลพื้นฐาน
        if not username or not email or not password or not confirm_password:
            flash("กรุณากรอกข้อมูลให้ครบถ้วน", "warning")
            return redirect(url_for('register_login'))

        # ตรวจรหัสผ่านกับรหัสผ่านยืนยัน
        if password != confirm_password:
            flash("รหัสผ่านไม่ตรงกัน", "warning")
            return redirect(url_for('register_login'))

        if len(password) < 8:
            flash("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร", "warning")
            return redirect(url_for('register_login'))

        # ตรวจชื่อผู้ใช้หรืออีเมลซ้ำ
        exists = username_or_email_exists(username, email)
        if exists:
            existing_username, existing_email = exists
            if username == existing_username:
                flash("ชื่อผู้ใช้นี้มีอยู่แล้ว", "danger")
            elif email == existing_email:
                flash("อีเมลนี้มีผู้ใช้แล้ว", "danger")
            return redirect(url_for('register_login'))

        # ตรวจว่ามีผู้ใช้ในระบบแล้วหรือยัง
        conn = sqlite3.connect(get_db_path('users.db'))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        conn.close()

        # ถ้าสมัครเป็นคนแรก → เป็น admin
        if user_count == 0:
            role = 'admin'
            is_verified = 1
            flash("บัญชีแรกของระบบจะถูกตั้งเป็นผู้ดูแล (Admin)", "info")
        else:
            # ถัดจากนั้น ใช้กฎปกติ (patient ยืนยันเอง / doctor ต้องรอ admin)
            is_verified = 1 if role == 'patient' else 0

        # สร้าง OTP และเก็บข้อมูลใน session รอ confirm
        otp = generate_otp()
        session['register_pending_user'] = {
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'otp': otp,
            'otp_created_at': datetime.now().isoformat(),
            'role': role,
            'is_verified': is_verified
        }

        print("Sending OTP to", email)
        send_otp_email(email, username, otp, purpose="register")
        flash("กรุณายืนยัน OTP ที่ส่งไปยังอีเมลของคุณ", "info")
        return redirect(url_for('register_verify_otp'))

    return render_template('register_login.html')

# ส่ง OTP อีกรอบหน้า register_login
@app.route('/resend_register_otp', methods=['POST'])
def resend_register_otp():
    register_pending_user = session.get('register_pending_user')
    if not register_pending_user:
        return jsonify(success=False, message="ไม่พบข้อมูลสำหรับลงทะเบียน กรุณาเริ่มขั้นตอนใหม่"), 400
  
    username = register_pending_user['username']
    email = register_pending_user['email']
    otp = generate_otp()
    
    register_pending_user['otp'] = otp
    register_pending_user['otp_created_at'] = datetime.now().isoformat()
    session['register_pending_user'] = register_pending_user

    send_otp_email(email, username, otp, purpose="register")

    # คำนวณเวลาหมดอายุ OTP (ในหน่วย milliseconds)
    expire_timestamp = int((datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)).timestamp() * 1000)

    return jsonify(
        success=True, 
        message="ส่งรหัส OTP ใหม่ไปที่อีเมลแล้ว", 
        expire_timestamp=expire_timestamp,)

# ส่ง OTP อีกรอบหน้า forgot_password
@app.route('/resend_reset_otp', methods=['POST'])
def resend_reset_otp():
    reset_pending_user = session.get('reset_pending_user')
    if not reset_pending_user:
        return jsonify(success=False, message="ไม่พบข้อมูลสำหรับรีเซ็ตรหัสผ่าน กรุณาเริ่มขั้นตอนใหม่"), 400

    email = reset_pending_user['email']
    username = reset_pending_user['username']  
    otp = generate_otp()
    reset_pending_user['otp'] = otp
    reset_pending_user['otp_created_at'] = datetime.now().isoformat()
    session['reset_pending_user'] = reset_pending_user
    send_otp_email(email, username, otp, purpose="reset")
    expire_timestamp = int((datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)).timestamp() * 1000)

    return jsonify(
        success=True, 
        message="ส่งรหัส OTP ใหม่ไปที่อีเมลแล้ว", 
        expire_timestamp=expire_timestamp,
        )

@app.route('/register_verify_otp', methods=['GET', 'POST'])
def register_verify_otp():
    register_pending_user = session.get('register_pending_user')
    if not register_pending_user:
        flash("เกิดข้อผิดพลาด กรุณาลงทะเบียนใหม่", "danger")
        return redirect(url_for('register_login'))

    try:
        otp_created_at = datetime.fromisoformat(register_pending_user['otp_created_at'])
    except Exception:
        flash("ข้อมูลไม่ถูกต้อง กรุณาลงทะเบียนใหม่", "danger")
        session.pop('register_pending_user', None)
        return redirect(url_for('register_login'))

    # ตรวจหมดอายุทันที (หากแสดงหน้า GET)
    if datetime.now() - otp_created_at > timedelta(minutes=OTP_EXPIRE_MINUTES):
        flash("รหัสยืนยันหมดอายุ กรุณาลงทะเบียนใหม่", "danger")
        session.pop('register_pending_user', None)
        return redirect(url_for('register_login'))

    if request.method == 'POST':
        input_otp = request.form.get('otp')

        if input_otp == register_pending_user['otp']:
            role = register_pending_user.get('role', 'patient')
            is_verified = 1 if role == 'patient' else 0  # ผู้ป่วยยืนยันเอง, หมอต้องรอ admin

            # บันทึกผู้ใช้ลงฐานข้อมูลจริง
            conn = sqlite3.connect(get_db_path('users.db'))
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, email, password, role, is_verified) VALUES (?, ?, ?, ?, ?)",
                (
                    register_pending_user['username'],
                    register_pending_user['email'],
                    register_pending_user['password'],
                    role,
                    is_verified
                )
            )
            conn.commit()
            conn.close()

            session.pop('register_pending_user', None)
            flash("ยืนยันตัวตนสำเร็จ สามารถเข้าสู่ระบบได้แล้ว", "success")
            if role == 'patient':
                flash("สามารถเข้าสู่ระบบได้แล้ว", "success")
            else:
                flash("รอผู้ดูแลระบบอนุมัติบัญชี", "info")
            return redirect(url_for('login'))

    # ส่ง timestamp ที่ OTP จะหมดอายุ
    expire_timestamp = int((datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)).timestamp() * 1000)
    username = register_pending_user['username']
                                     
    return render_template(
        'register_verify_otp.html',
        email=register_pending_user['email'],
        OTP_EXPIRE_MINUTES=OTP_EXPIRE_MINUTES,
        otp_expire_timestamp=expire_timestamp,
        register_pending_user=username,
        otp_flow_type="register"  
    )

# สร้าง ส่ง otp แล้วในหน้านี้
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username').strip()

        # ล้าง OTP เก่าจาก session
        session.pop('reset_pending_user', None)

        with sqlite3.connect(get_db_path('users.db')) as conn:
            c = conn.cursor()
            c.execute("SELECT email FROM users WHERE username = ?", (username,))
            row = c.fetchone()

            if not row:
                flash("ไม่พบบัญชีผู้ใช้", "danger")
                return redirect(url_for('forgot_password'))

            email = row[0]

            # สร้าง OTP ใหม่
            otp = generate_otp()
            otp_created_at = datetime.now()

            # บันทึก OTP และเวลาสร้างใน DB
            c.execute(
                "UPDATE users SET otp = ?, otp_created_at = ? WHERE username = ?",
                (otp, otp_created_at.strftime('%Y-%m-%d %H:%M:%S'), username)
            )
            conn.commit()

        expire_timestamp = int((datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)).timestamp() * 1000)

        # เก็บข้อมูลใน session
        session['reset_pending_user'] = {
            'username': username,
            'email': email,
            'otp': otp,
            'otp_created_at': otp_created_at.isoformat(),
            'otp_expire_timestamp': expire_timestamp
        }

        send_otp_email(email, username, otp, purpose="reset")

        flash("ส่งรหัส OTP ไปยังอีเมลของคุณแล้ว", "success")
        return redirect(url_for('reset_verify_otp'))

    # GET request
    return render_template(
        'forgot_password.html',
        OTP_EXPIRE_MINUTES=OTP_EXPIRE_MINUTES,
        otp_expire_timestamp=None  # ป้องกัน Undefined
    )

@app.route('/reset_verify_otp', methods=['GET', 'POST'])
def reset_verify_otp():
    reset_pending_user = session.get('reset_pending_user')
    if not reset_pending_user:
        flash("กรุณาเริ่มต้นกระบวนการรีเซ็ตรหัสผ่านใหม่", "danger")
        return redirect(url_for('forgot_password'))

    try:
        otp_created_at = datetime.fromisoformat(reset_pending_user['otp_created_at'])
    except Exception:
        flash("ข้อมูลไม่ถูกต้อง กรุณาเริ่มต้นใหม่", "danger")
        session.pop('reset_pending_user', None)
        return redirect(url_for('forgot_password'))

    # ตรวจสอบหมดอายุ OTP ก่อน
    if datetime.now() - otp_created_at > timedelta(minutes=OTP_EXPIRE_MINUTES):
        flash("รหัส OTP หมดอายุ กรุณาขอรหัสใหม่", "danger")
        session.pop('reset_pending_user', None)
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        input_otp = request.form.get('otp')

        if input_otp == reset_pending_user['otp']:
            session['otp_verified'] = True
            session['reset_username'] = reset_pending_user['username']  # เตรียมไว้ใช้ตอน reset_password
            flash("ยืนยัน OTP สำเร็จ กรุณาตั้งรหัสผ่านใหม่", "success")
            session.pop('reset_pending_user', None)
            return redirect(url_for('reset_password'))
        else:
            flash("รหัส OTP ไม่ถูกต้อง กรุณาลองใหม่", "danger")

    # ส่ง timestamp ที่ OTP จะหมดอายุ
    expire_timestamp = int((otp_created_at + timedelta(minutes=OTP_EXPIRE_MINUTES)).timestamp() * 1000)

    return render_template(
        'reset_verify_otp.html',
        email=reset_pending_user['email'],
        OTP_EXPIRE_MINUTES=OTP_EXPIRE_MINUTES,
        otp_expire_timestamp=expire_timestamp,
        reset_pending_username=reset_pending_user['username'],
        otp_flow_type="reset"  
    )

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_username' not in session or 'otp_verified' not in session:
        flash("กรุณาเริ่มต้นกระบวนการรีเซ็ตรหัสผ่านใหม่อีกครั้ง", "warning")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("รหัสผ่านไม่ตรงกัน กรุณาลองใหม่", "danger")
            return render_template('reset_password.html')

        hashed_password = generate_password_hash(new_password)
        username = session.get('reset_username')

        with sqlite3.connect(get_db_path('users.db')) as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE users SET password = ?, otp = NULL, otp_created_at = NULL WHERE username = ?",
                (hashed_password, username)
            )
            conn.commit()

        # ล้าง session ที่เกี่ยวข้อง
        session.pop('reset_username', None)
        session.pop('otp_verified', None)

        flash("รีเซ็ตรหัสผ่านสำเร็จ สามารถเข้าสู่ระบบได้แล้ว", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/')
@login_required()
def home():
    username = session.get('user')
    role = session.get('role')  

    if not username:
        flash("กรุณาเข้าสู่ระบบก่อน", "warning")
        return redirect(url_for('login'))

    if role == 'doctor':
        video_link = url_for('videocall_doctor')
    elif role == 'patient':
        video_link = url_for('videocall_patient')
    else:
        video_link = None

    return render_template('home.html', current_user=username, role=role, video_link=video_link)

@app.route('/view_table/<table_name>')
@login_required(role='admin')
def view_table(table_name):
    if session.get('role') != 'admin':
        flash("คุณไม่มีสิทธิ์เข้าถึงหน้านี้", "danger")
        return redirect(url_for('home'))

    # กำหนด mapping: table_name → database file + display name
    tables = {
        "users": ("users.db", "บัญชีผู้ใช้"),
        "patient": ("patient.db", "ผู้ป่วย"),
        "learn": ("learn.db", "การให้ความรู้"),
        "followup": ("followup.db", "ติดตามอาการ")
    }

    if table_name not in tables:
        flash("ฐานข้อมูลไม่ถูกต้อง", "danger")
        return redirect(url_for('home'))

    db_file, display_name = tables[table_name]

    # อ่านข้อมูลจากฐาน
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    data = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    conn.close()

    return render_template('view_table.html', data=data, table_name=display_name)

def init_patient_db():
    with sqlite3.connect("patient.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS patient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                HN TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                birth_date INTEGER NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT,
                disease TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        ''')
        conn.commit()

@app.route('/register_patient', methods=['GET', 'POST'])
@login_required()
def register_patient():
    username = session.get('user')
    if not username:
        flash("ไม่พบข้อมูลผู้ใช้", "error")
        return jsonify({"error": "ไม่พบข้อมูลผู้ใช้"}), 401
    
    print(request.form)

    if request.method == 'POST':
        HN = request.form['HN']
        name = request.form['name']
        birth_date = request.form['birthDate']
        gender = request.form['gender']
        phone = request.form.get('phone')
        disease = request.form.get('disease', 'ไม่มี')

        # ตรวจสอบค่าว่าง
        if not HN or not name or not birth_date or not gender:
            flash("กรุณากรอกข้อมูลให้ครบ", "error")
            return jsonify({"error": "กรุณากรอกข้อมูลให้ครบ"}), 400
        
        # บันทึกลงฐานข้อมูล SQLite
        with sqlite3.connect("patient.db") as conn:
            cursor = conn.cursor()
            # เช็ก HN ซ้ำ
            cursor.execute(
                "SELECT 1 FROM patient WHERE HN = ? AND username = ?",
                (HN, username)
            )
            if cursor.fetchone():
                flash("HN นี้มีอยู่แล้วในบัญชีคุณ", "info")
                return jsonify({"error": "HN นี้มีอยู่แล้วในบัญชีคุณ"}), 400
                
            # ถ้าไม่มี → insert ใหม่
            cursor.execute(
                "INSERT INTO patient (HN, name, birth_date, gender, phone, disease, username) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (HN, name, birth_date, gender, phone, disease, username)
            )
            conn.commit()
        
        flash("บันทึกผู้ป่วยใหม่เรียบร้อยแล้ว", "success")

        session['last_patient'] = {
            "HN": HN,
            "name": name,
            "birthDate": birth_date,
            "gender": gender,
            "phone": phone,
            "disease": disease
        }

        return jsonify(session['last_patient'])
    
    last_patient = None
    # ตรวจสอบ session ก่อน
    if 'last_patient' in session:
        last_patient = session['last_patient']
        # เช็กว่ามีอยู่จริงใน DB
        with sqlite3.connect("patient.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM patient WHERE HN = ? AND username = ?", 
                           (last_patient['HN'], username))
            if not cursor.fetchone():
                last_patient = None
                session.pop('last_patient', None)

    # ถ้าไม่มีใน session → ดึงจาก DB ล่าสุด
    if not last_patient:
        with sqlite3.connect("patient.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT HN, name, birth_date, gender, phone, disease "
                "FROM patient WHERE username = ? ORDER BY rowid DESC LIMIT 1",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                last_patient = {
                    "HN": row[0],
                    "name": row[1],
                    "birthDate": row[2],
                    "gender": row[3],
                    "phone": row[4],
                    "disease": row[5]
                }
                session['last_patient'] = last_patient

    return render_template('register_patient.html', last_patient=last_patient)

@app.route('/patients')
@login_required()
def get_patients():
    username = session.get('user')
    with sqlite3.connect("patient.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient WHERE username = ? ORDER BY created_at DESC", (username,))
        patients = [dict(row) for row in cursor.fetchall()]
    return jsonify(patients)

def init_learn_db():
    with sqlite3.connect("learn.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS learn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                topic_id TEXT NOT NULL,        
                pre_score REAL,
                learn_completed BOOLEAN DEFAULT 0,
                post_score REAL,            
                completed_at TEXT
            );
        ''')

@app.route('/learn')
@login_required()
def learn():
    username = session.get('user')
    role = session.get('role')  # สมมติว่าเก็บ role ไว้ใน session ตอน login
    
    last_patient = None

    # เฉพาะผู้ใช้ role 'patient' หรือ 'admin' ที่ต้องลงทะเบียนผู้ป่วย
    if role in ['patient', 'admin']:  # สมมติ 'admin_patient' คือ admin ที่ต้องลงทะเบียนผู้ป่วย
        with sqlite3.connect("patient.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT HN, name, birth_date, gender, phone, disease "
                "FROM patient WHERE username = ? ORDER BY created_at DESC LIMIT 1",
                (username,)
            )
            row = cursor.fetchone()

            if not row:
                flash("กรุณาลงทะเบียนผู้ป่วยก่อน เพื่อเข้าใช้งานระบบ", "warning")
                return redirect(url_for('register_patient'))

            last_patient = {
                "HN": row[0],
                "name": row[1],
                "birthDate": row[2],
                "gender": row[3],
                "phone": row[4],
                "disease": row[5]
            }
            session['last_patient'] = last_patient

    # สำหรับผู้ใช้ role อื่น ไม่ต้องลงทะเบียนผู้ป่วย
    return render_template('learn.html', current_user=username, patient=last_patient)


def save_progress_db(username, topic_id, pre_score=None, learn_completed=None, post_score=None, completed_at=None):
    with sqlite3.connect("learn.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM learn WHERE username=? AND topic_id=?", (username, topic_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE learn
                SET pre_score = COALESCE(?, pre_score),
                    learn_completed = COALESCE(?, learn_completed),
                    post_score = COALESCE(?, post_score),
                    completed_at = COALESCE(?, completed_at)
                WHERE id = ?
            """, (pre_score, learn_completed, post_score, completed_at, row[0]))
        else:
            cursor.execute("""
                INSERT INTO learn (username, topic_id, pre_score, learn_completed, post_score, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, topic_id, pre_score, learn_completed, post_score, completed_at))
        conn.commit()

def get_progress_db(username):
    with sqlite3.connect("learn.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic_id, pre_score, learn_completed, post_score, completed_at FROM learn WHERE username=?", (username,))
        rows = cursor.fetchall()
        progress = {}
        for topic_id, pre_score, learn_completed, post_score, completed_at in rows:
            progress[topic_id] = {
                "pretest": pre_score is not None,
                "learn": bool(learn_completed),  
                "posttest": post_score is not None,
                "pre_score": pre_score,
                "post_score": post_score,
                "completed_at": completed_at
            }
        return progress

@app.route('/api/progress', methods=['GET', 'POST'])
def handle_progress():
    if request.method == 'GET':
        username = request.args.get('username', 'guest')
        try:
            progress = get_progress_db(username)
            if not progress:
                progress = {
                    'topic1': {'pretest': False, 'learn': False, 'posttest': False},
                    'topic2': {'pretest': False, 'learn': False, 'posttest': False},
                    'topic3': {'pretest': False, 'learn': False, 'posttest': False}
                }
            return jsonify({'success': True, 'progress': progress})
        except Exception as e:
            print(f'Error getting progress: {str(e)}')
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            progress = data.get('progress')  # รับ progress object ทั้งหมด
            
            # บันทึก progress ลง database
            if progress:
                for topic_id, steps in progress.items():
                    pre_score = 100 if steps.get('pretest') else None
                    post_score = 100 if steps.get('posttest') else None
                    completed_at = datetime.now().isoformat() if steps.get('posttest') else None
                    
                    save_progress_db(username, topic_id, pre_score, post_score, completed_at)
            
            return jsonify({'success': True, 'message': 'Progress saved to DB successfully'})
        except Exception as e:
            print(f'Error saving progress: {str(e)}')
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/topics', methods=['GET'])
def get_topics():
    topics = {
        'topic1': {'id': 'topic1', 'title': 'พื้นฐานการเขียนโปรแกรม', 'description': 'เรียนรู้พื้นฐาน', 'icon': '💻'},
        'topic2': {'id': 'topic2', 'title': 'โครงสร้างข้อมูลและอัลกอริทึม', 'description': 'เรียนรู้โครงสร้างข้อมูล', 'icon': '🔧'},
        'topic3': {'id': 'topic3', 'title': 'การพัฒนาเว็บไซต์', 'description': 'HTML, CSS, JS', 'icon': '🌐'}
    }
    return jsonify({'success': True, 'topics': topics})

@app.route('/api/content/<topic_id>/<step_id>', methods=['GET'])
def get_content(topic_id, step_id):
    content_data = {
        'topic1': {'pretest': {'title':'ก่อนเรียน','questions':[{'id':'q1','question':'อะไรคือโปรแกรม?','type':'multiple_choice','options':['A','B','C','D']}]}, 
                   'learn': {'title':'เรียน','sections':[{'title':'แนวคิด','content':'...'}]}, 
                   'posttest': {'title':'หลังเรียน','questions':[{'id':'q1','question':'อธิบายแนวคิด','type':'essay'}]}},
        'topic2': {'pretest': {}, 'learn': {}, 'posttest': {}},
        'topic3': {'pretest': {}, 'learn': {}, 'posttest': {}}
    }
    if topic_id in content_data and step_id in content_data[topic_id]:
        return jsonify({'success': True, 'content': content_data[topic_id][step_id]})
    else:
        return jsonify({'success': False, 'error': 'Content not found'}), 404
    
@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.get_json()
        username = data.get('username')
        topic_id = data.get('topic_id')
        step_id = data.get('step_id')
        score = data.get('score', 0)
        
        print(f'📝 Submit answer: {username}, {topic_id}, {step_id}, score={score}')
        
        # บันทึกคะแนนลง database
        if step_id == 'pretest':
            save_progress_db(username, topic_id, pre_score=score)
        elif step_id == 'learn':
            save_progress_db(username, topic_id, learn_completed=1)
        elif step_id == 'posttest':
            save_progress_db(username, topic_id, post_score=score, completed_at=datetime.now().isoformat())
        
        return jsonify({'success': True, 'score': score})
        
    except Exception as e:
        print(f'❌ Error submitting answer: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/static/<path:filename>')
def static_files(filename):
    try:
        if filename.endswith('.css'):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/css; charset=utf-8'}
        elif filename.endswith('.js'):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except FileNotFoundError:
        return "File not found", 404

def init_followup_db():
    with sqlite3.connect("followup.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS followup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                HN TEXT NOT NULL,
                followup_text TEXT,
                followup_date TEXT NOT NULL,
                UNIQUE(HN, followup_date)  -- ป้องกัน HN + วันที่ซ้ำ
            )
        ''')
        conn.commit()

# ฟังก์ชันดึง follow-ups
def get_all_followups():
    conn = sqlite3.connect("followup.db")
    conn.row_factory = sqlite3.Row
    followups = conn.execute("SELECT * FROM followup ORDER BY followup_date DESC").fetchall()
    conn.close()
    return [dict(f) for f in followups]

@app.route('/videocall/doctor')
@login_required(role='doctor')
def videocall_doctor():
    return render_template('videocall_doctor.html')

@app.route('/get_patient/<hn>', methods=['GET'])
@login_required()
def get_patient(hn):
    with sqlite3.connect("patient.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT HN, name FROM patient WHERE HN=?", (hn,))
        row = cursor.fetchone()
        if row:
            return jsonify({"HN": row[0], "name": row[1]})
        return jsonify({"error": "ไม่พบผู้ป่วย"}), 404

@app.route('/videocall_patient')
@login_required()
def videocall_patient():
    username = session.get('user')
    last_patient = session.get('last_patient')

    if not last_patient:
        # ถ้าไม่มีใน session ให้ลองดึงจาก DB
        with sqlite3.connect("patient.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT HN, name, birth_date, gender, phone, disease "
                "FROM patient WHERE username = ? ORDER BY created_at DESC LIMIT 1",
                (username,)
            )
            row = cursor.fetchone()
            
            if row:
                last_patient = {
                    "HN": row[0],
                    "name": row[1],
                    "birthDate": row[2],
                    "gender": row[3],
                    "phone": row[4],
                    "disease": row[5]
                }
                session['last_patient'] = last_patient
            else:
                # ถ้ายังไม่มีข้อมูลเลย ให้ redirect ไปหน้า register
                flash("กรุณาลงทะเบียนผู้ป่วยก่อน เพื่อเริ่มวิดีโอคอล", "warning")
                return redirect(url_for('register_patient'))

    return render_template('videocall_patient.html', patient=last_patient)

@app.route('/api/save_patient', methods=['POST'])
def save_patient():
    try:
        data = request.get_json()
        name = data.get('name')
        HN = data.get('HN')
        followup_text = data.get('notes', '')
        followup_date = data.get('followUpDate') or datetime.now().strftime("%Y-%m-%d")

        if not name or not HN:
            return jsonify({'success': False, 'error': 'ชื่อ-สกุล และ HN เป็นค่าจำเป็น'}), 400

        with sqlite3.connect("followup.db") as conn:
            cursor = conn.cursor()
            try:
                # พยายาม insert
                cursor.execute('''
                    INSERT INTO followup (patient_name, HN, followup_text, followup_date)
                    VALUES (?, ?, ?, ?)
                ''', (name, HN, followup_text, followup_date))
            except sqlite3.IntegrityError:
                # ถ้า HN + followup_date ซ้ำ → update แทน
                cursor.execute('''
                    UPDATE followup
                    SET followup_text = ?, patient_name = ?
                    WHERE HN = ? AND followup_date = ?
                ''', (followup_text, name, HN, followup_date))
            conn.commit()

        updated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return jsonify({'success': True, 'message': 'บันทึกข้อมูลเรียบร้อย', 'updated_at': updated_at})

    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'error': 'เกิดข้อผิดพลาดในการบันทึกข้อมูล'}), 500

@app.route('/api/followups', methods=['GET'])
def get_followups():
    try:
        followups = get_all_followups()
        return jsonify({'success': True, 'followups': followups})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@socketio.on('join')
def on_join(data):
    room = data['room']
    username = data['username']
    join_room(room)
    print(f"[JOIN] {username} joined room: {room}")
    emit('user_joined', {'username': username}, room=room, include_self=False)

@socketio.on('offer')
def on_offer(data):
    room = data['room']
    print(f"[OFFER] Received offer for room: {room}")
    emit('offer_received', {
        'sdp': data['sdp'],
        'type': data['type']
    }, room=room, include_self=False)

@socketio.on('answer')
def on_answer(data):
    room = data['room']
    print(f"[ANSWER] Received answer for room: {room}")
    emit('answer_received', {
        'sdp': data['sdp'],
        'type': data['type']
    }, room=room, include_self=False)

@socketio.on('ice_candidate')
def on_ice_candidate(data):
    room = data['room']
    print(f"[ICE] Received ICE candidate for room: {room}")
    emit('ice_candidate_received', {
        'candidate': data['candidate']
    }, room=room, include_self=False)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    username = data.get('username', 'User')
    leave_room(room)
    print(f"[LEAVE] {username} left room: {room}")
    emit('user_left', {'username': username}, room=room)

@socketio.on('disconnect')
def on_disconnect():
    print("[DISCONNECT] User disconnected")

@app.route('/api/check_patient/<hn>', methods=['GET'])
@login_required()
def check_patient(hn):
    print(f"[DEBUG] Checking patient with HN: {hn}")
    username = session.get('user')
    print(f"[DEBUG] Current user: {username}")
    try:
        with sqlite3.connect("patient.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT HN, name, birth_date, gender, phone, disease FROM patient WHERE HN=?", (hn,))
            row = cursor.fetchone()
            print(f"[DEBUG] Database result: {row}")
            if row:
                return jsonify({
                    "success": True,
                    "HN": row[0],
                    "name": row[1],
                    "birthDate": row[2],
                    "gender": row[3],
                    "phone": row[4],
                    "disease": row[5]
                })
            else:
                return jsonify({"success": False, "error": "ไม่พบผู้ป่วย"}), 404
    except Exception as e:
        print(f"[ERROR] Database error: {str(e)}")
        return jsonify({"success": False, "error": "เกิดข้อผิดพลาดในการค้นหาข้อมูล"}), 500

if __name__ == '__main__':
    init_users_db()
    init_patient_db()
    init_learn_db()
    init_followup_db()

    # ใช้ socketio.run() แทน app.run()
    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True  # สำหรับ development เท่านั้น
    )
