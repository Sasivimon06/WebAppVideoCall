from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import random
from werkzeug.security import check_password_hash,generate_password_hash
from dateutil.relativedelta import relativedelta
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from aiortc import RTCPeerConnection, RTCSessionDescription  # สำหรับ WebRTC
import json

app = Flask(__name__)
app.secret_key = 'this_is_a_test_key_for_demo'
RFID_API_KEY = "my_secure_token_only_for_demo"  
socketio = SocketIO(app, cors_allowed_origins="*")
pcs = {}  # Dictionary เพื่อเก็บ peer connections ตาม room/user

OTP_EXPIRE_MINUTES = 3
RESEND_WAIT_SECONDS = 60
MAX_LOGIN_ATTEMPTS = 5    # login ผิดได้ไม่เกิน 5 ครั้งใน 10 นาที
BLOCK_TIME_MINUTES = 10

app.config.update(
    MAIL_SERVER='smtp.gmail.com',  # ตัวอย่าง: smtp.gmail.com, หรือ SMTP เซิร์ฟเวอร์ของคุณ
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='sasivimon.0606@gmail.com',   # อีเมลผู้ส่ง (ต้องเป็นของโดเมนคุณ)
    MAIL_PASSWORD='rulnyhqjunfxeobz',
    MAIL_DEFAULT_SENDER=('ระบบยืนยันตัวตน', 'sasivimon.0606@gmail.com')  # ชื่อแสดงและอีเมลผู้ส่ง
)

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

# Database 
def init_users_db():
    conn = sqlite3.connect('users.db')
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

""" conn = sqlite3.connect('users.db')
c = conn.cursor()

init_users_db()

username = 'admin'
password = generate_password_hash('admin123456')
email = 'eye.sasiwimon999@gmail.com'
role = 'admin'
is_verified = 1

c.execute(
    "INSERT INTO users (username, email, password, role, is_verified) VALUES (?, ?, ?, ?, ?)",
    (username, email, password, role, is_verified)
)
conn.commit()
conn.close()
print("Admin user created!") """

def create_user(username, password, email):
    conn = sqlite3.connect('users.db')
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
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users WHERE role = 'doctor' AND is_verified = 0")
    doctors = c.fetchall()
    conn.close()
    return render_template('pending_doctors.html', doctors=doctors)

@app.route('/admin/approve_doctor/<int:doctor_id>', methods=['POST'])
@login_required(role='admin')
def approve_doctor(doctor_id):
    conn = sqlite3.connect('users.db')
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
        role = request.form['role']  # doctor / patient
        is_verified = 1  # admin อนุมัติแล้ว

        with sqlite3.connect('users.db') as conn:
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
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# ตรวจสอบว่าในฐานข้อมูลมีชื่อผู้ใช้และอีเมลที่รับเข้ามานั้นอยู่แล้วหรือไม่ เพื่อป้องกันการสมัครซ้ำด้วยชื่อผู็ใช้,อีเมลเดียวกัน
def username_or_email_exists(username, email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email))
    row = c.fetchone()
    conn.close()
    return row if row else None

# ตรวจสอบว่า username มีค่าแน่ ๆ ก่อนใช้
def get_user(username):
    if not username:
        return None  # ป้องกันกรณี username เป็น None หรือว่าง
    conn = sqlite3.connect('users.db')
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
            body = (
                f"เรียนคุณ {username},\n\n"
                f"รหัส OTP ของคุณสำหรับการลงทะเบียนคือ: {otp}\n"
                f"รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที\n\n"
                f"หากคุณไม่ได้ร้องขอ โปรดเพิกเฉยต่ออีเมลฉบับนี้\n\n"
            )
        elif purpose == "reset":
            subject = "รหัส OTP สำหรับรีเซ็ตรหัสผ่าน"
            body = (
                f"เรียนคุณ {username},\n\n"
                f"รหัส OTP ของคุณสำหรับการรีเซ็ตรหัสผ่านคือ: {otp}\n"
                f"รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที\n\n"
                f"หากคุณไม่ได้ร้องขอ โปรดเพิกเฉยต่ออีเมลฉบับนี้\n\n"
            )
        else:
            subject = "รหัส OTP"
            body = (
                f"เรียนคุณ {username},\n\n"
                f"รหัส OTP ของคุณคือ: {otp}\n"
                f"รหัสนี้จะหมดอายุใน {OTP_EXPIRE_MINUTES} นาที\n\n"
            )

        msg = Message(
            subject=subject,
            sender=("ระบบยืนยันตัวตน", "your_email@gmail.com"),
            recipients=[email]
        )
        msg.body = body
        print("ก่อนส่งเมล")
        mail.send(msg)
        print("ส่งเมลสำเร็จ")
        print(f"[INFO] ส่งอีเมล OTP เรียบร้อยแล้ว: {email}")
    except Exception as e:
        print("[ERROR] การส่งอีเมลล้มเหลว:", e)

@app.route('/register_login', methods=['GET', 'POST'])
def register_login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()
        role = request.form.get('role')  # ฟอร์มมี select role: patient / doctor

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

        # สร้าง OTP และเก็บข้อมูลใน session รอ confirm
        otp = generate_otp()
        
        is_verified = 1 if role == 'patient' else 0  # ผู้ป่วยยืนยันเอง, หมอต้องรอ admin

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
            conn = sqlite3.connect('users.db')
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

    # ส่ง timestamp ที่ OTP จะหมดอายุ (milliseconds for JS)
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

        with sqlite3.connect('users.db') as conn:
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

    # ตรวจสอบหมดอายุ OTP ก่อน (ตอน GET)
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

    # ส่ง timestamp ที่ OTP จะหมดอายุ (milliseconds for JS)
    expire_timestamp = int((otp_created_at + timedelta(minutes=OTP_EXPIRE_MINUTES)).timestamp() * 1000)

    return render_template(
        'reset_verify_otp.html',
        email=reset_pending_user['email'],
        OTP_EXPIRE_MINUTES=OTP_EXPIRE_MINUTES,
        otp_expire_timestamp=expire_timestamp,
        reset_pending_username=reset_pending_user['username'],
        otp_flow_type="reset"  # สำหรับใช้ใน JS หรือ Template แยก flow
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

        with sqlite3.connect('users.db') as conn:
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
    role = session.get('role')  # เก็บ role แยกใน session

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

""" # หน้า Home สำหรับ Doctor
@app.route('/doctor/home')
@login_required(role='doctor')
def doctor_home():
    username = session.get('user')
    # โหลดข้อมูลเฉพาะหมอ เช่น รายชื่อผู้ป่วย, นัดหมาย ฯลฯ
    return render_template('doctor_home.html', current_user=username)

# หน้า Home สำหรับ Patient
@app.route('/patient/home')
@login_required(role='patient')
def patient_home():
    username = session.get('user')
    # โหลดข้อมูลเฉพาะผู้ป่วย เช่น ประวัติ, วิดีโอคอลกับหมอ ฯลฯ
    return render_template('patient_home.html', current_user=username)
 """
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
            # 🔹 เช็ก HN ซ้ำ
            cursor.execute(
                "SELECT 1 FROM patient WHERE HN = ? AND username = ?",
                (HN, username)
            )
            if cursor.fetchone():
                flash("HN นี้มีอยู่แล้วในบัญชีคุณ", "info")
                return jsonify({"error": "HN นี้มีอยู่แล้วในบัญชีคุณ"}), 400
                
            # 🔹 ถ้าไม่มี → insert ใหม่
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
    username = session['user']  # session['user'] เป็น str ของ username
    return render_template('learn.html', current_user=username)

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
        cursor.execute("SELECT topic_id, pre_score, post_score, completed_at FROM learn WHERE username=?", (username,))
        rows = cursor.fetchall()
        progress = {}
        for topic_id, pre_score, post_score, completed_at in rows:
            progress[topic_id] = {
                "pretest": pre_score is not None,
                "learn": learn_completed is True,
                "posttest": post_score is not None,
                "pre_score": pre_score,
                "post_score": post_score,
                "completed_at": completed_at
            }
        return progress

@app.route('/api/progress', methods=['GET'])
def get_progress():
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/progress', methods=['POST'])
def save_progress():
    try:
        data = request.get_json()
        username = data['username']
        topic_id = data['topic_id']
        pre_score = data.get('pre_score')
        post_score = data.get('post_score')
        completed_at = data.get('completed_at')

        save_progress_db(username, topic_id, pre_score, post_score, completed_at)

        return jsonify({'success': True, 'message': 'Progress saved to DB successfully'})
    except Exception as e:
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
    data = request.get_json()
    username = data.get('username')
    topic_id = data.get('topic_id')
    step_id = data.get('step_id')
    score = data.get('score')  # รับคะแนนจาก JS

    # สมมุติ completed_at สำหรับ posttest
    completed_at = datetime.now().isoformat() if step_id == 'posttest' else None

    if step_id == 'pretest':
        save_progress_db(username, topic_id, pre_score=score)
    elif step_id == 'posttest':
        save_progress_db(username, topic_id, post_score=score, completed_at=completed_at)
    else:  # learn
        save_progress_db(username, topic_id)

    return jsonify({'success': True, 'score': score, 'message': 'Answer submitted'})

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
def get_patient(HN):
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
    
    # ดึงข้อมูลผู้ป่วยล่าสุดจาก session
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

# เพิ่ม route สำหรับตรวจสอบ HN
@app.route('/api/check_patient/<hn>', methods=['GET'])
@login_required()
def check_patient(hn):
    username = session.get('user')
    with sqlite3.connect("patient.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT HN, name FROM patient WHERE HN=? AND username=?", (hn, username))
        row = cursor.fetchone()
        if row:
            return jsonify({"success": True, "HN": row[0], "name": row[1]})
        return jsonify({"success": False, "error": "ไม่พบผู้ป่วย"}), 404

if __name__ == '__main__':
    # เตรียมการข้อมูลสำหรับผู้ใช้งานและอุปกรณ์
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
