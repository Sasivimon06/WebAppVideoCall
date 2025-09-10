from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import sqlite3
from datetime import datetime, UTC, timedelta
from functools import wraps
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import random, os, shutil
from werkzeug.security import check_password_hash,generate_password_hash
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
DATABASE = '"patients.db"'
app.secret_key = 'this_is_a_test_key_for_demo'
RFID_API_KEY = "my_secure_token_only_for_demo"  

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

""" with app.app_context():
    try:
        msg = Message("ทดสอบส่ง OTP", recipients=["friend@example.com"])
        msg.body = "นี่คือข้อความทดสอบส่ง OTP"
        mail.send(msg)
        print("ส่งสำเร็จ ✅")
    except Exception as e:
        print("ส่งไม่สำเร็จ ❌", e) """

# Database 
def init_users_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        is_verified INTEGER DEFAULT 0,
        otp TEXT,
        otp_created_at TEXT
    )''')
    conn.commit()
    conn.close()

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("กรุณาเข้าสู่ระบบก่อน", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
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
            hashed_password, is_verified = user[1], user[2]
            if is_verified != 1:
                flash("บัญชียังไม่ได้ยืนยันอีเมล", "warning")
            elif check_password_hash(hashed_password, password):
                # ล็อกอินสำเร็จ ล้างตัวแปร session
                session['user'] = user[0]
                session['login_attempts'] = 0
                session.permanent = True
                print("Login success, session set:", session)
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
    cursor.execute("SELECT username, password, is_verified FROM users WHERE username = ?", (username,))
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
        session['register_pending_user'] = {
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'otp': otp,
            'otp_created_at': datetime.now().isoformat()
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
            # บันทึกผู้ใช้ลงฐานข้อมูลจริง
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, email, password, is_verified) VALUES (?, ?, ?, 1)",
                (register_pending_user['username'], register_pending_user['email'], register_pending_user['password'])
            )
            conn.commit()
            conn.close()

            session.pop('register_pending_user', None)
            flash("ยืนยันตัวตนสำเร็จ สามารถเข้าสู่ระบบได้แล้ว", "success")
            return redirect(url_for('login'))
        else:
            flash("รหัสยืนยันไม่ถูกต้อง กรุณาลองใหม่", "danger")

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

def init_patients_db():
    with sqlite3.connect("patients.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                HN TEXT NOT NULL,
                followup_text TEXT NOT NULL,
                followup_date TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/')
@login_required
def home():
    return render_template('home.html')

def init_learn_db():
    with sqlite3.connect("learn.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS learn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                lesson_id INTEGER NOT NULL,        
                score_before REAL,
                score_after REAL,
                time_spent INTEGER,               
                completed_at TEXT
            );
        ''')
    conn.commit()

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """ดึงข้อมูลความคืบหน้าของผู้เรียน"""
    try:
        # ในการใช้งานจริง ควรมีระบบ authentication เพื่อแยกข้อมูลของแต่ละผู้ใช้
        user_id = request.args.get('user_id', 'default_user')
        
        if user_id in progress_data:
            return jsonify({
                'success': True,
                'progress': progress_data[user_id]['progress'],
                'last_updated': progress_data[user_id]['timestamp']
            })
        else:
            # ส่งค่าเริ่มต้น
            default_progress = {
                'topic1': {'pretest': False, 'learn': False, 'posttest': False},
                'topic2': {'pretest': False, 'learn': False, 'posttest': False},
                'topic3': {'pretest': False, 'learn': False, 'posttest': False}
            }
            return jsonify({
                'success': True,
                'progress': default_progress
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/progress', methods=['POST'])
def save_progress():
    """บันทึกความคืบหน้าของผู้เรียน"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        
        progress_data[user_id] = {
            'progress': data['progress'],
            'timestamp': data['timestamp']
        }
        
        # บันทึกลงไฟล์ (ในการใช้งานจริงควรใช้ฐานข้อมูล)
        save_to_file()
        
        return jsonify({
            'success': True,
            'message': 'Progress saved successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """ดึงข้อมูลหัวข้อทั้งหมด"""
    topics = {
        'topic1': {
            'id': 'topic1',
            'title': 'หัวข้อที่ 1: พื้นฐานการเขียนโปรแกรม',
            'description': 'เรียนรู้พื้นฐานการเขียนโปรแกรมและแนวคิดสำคัญ',
            'icon': '💻'
        },
        'topic2': {
            'id': 'topic2',
            'title': 'หัวข้อที่ 2: โครงสร้างข้อมูลและอัลกอริทึม',
            'description': 'ทำความเข้าใจโครงสร้างข้อมูลและอัลกอริทึมพื้นฐาน',
            'icon': '🔧'
        },
        'topic3': {
            'id': 'topic3',
            'title': 'หัวข้อที่ 3: การพัฒนาเว็บไซต์',
            'description': 'สร้างเว็บไซต์ด้วย HTML, CSS, และ JavaScript',
            'icon': '🌐'
        }
    }
    
    return jsonify({
        'success': True,
        'topics': topics
    })

@app.route('/api/content/<topic_id>/<step_id>', methods=['GET'])
def get_content(topic_id, step_id):
    """ดึงเนื้อหาของแต่ละขั้นตอน"""
    try:
        content_data = load_content_data()
        
        if topic_id in content_data and step_id in content_data[topic_id]:
            return jsonify({
                'success': True,
                'content': content_data[topic_id][step_id]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Content not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    """รับคำตอบจากผู้เรียน"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        topic_id = data.get('topic_id')
        step_id = data.get('step_id')
        answers = data.get('answers')
        
        # บันทึกคำตอบ
        answer_key = f"{user_id}_{topic_id}_{step_id}"
        save_answer(answer_key, answers)
        
        # ประเมินคะแนน (ตัวอย่าง)
        score = calculate_score(topic_id, step_id, answers)
        
        return jsonify({
            'success': True,
            'score': score,
            'message': 'Answer submitted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """ให้บริการไฟล์ static"""
    try:
        if filename == 'styles.css':
            with open('styles.css', 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/css; charset=utf-8'}
        elif filename == 'script.js':
            with open('script.js', 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except FileNotFoundError:
        return "File not found", 404

def save_to_file():
    """บันทึกข้อมูลลงไฟล์"""
    try:
        with open('progress_data.json', 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving to file: {e}")

def load_from_file():
    """โหลดข้อมูลจากไฟล์"""
    global progress_data
    try:
        if os.path.exists('progress_data.json'):
            with open('progress_data.json', 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
    except Exception as e:
        print(f"Error loading from file: {e}")

def load_content_data():
    """โหลดเนื้อหาการเรียน"""
    return {
        'topic1': {
            'pretest': {
                'title': 'แบบทดสอบก่อนเรียน: พื้นฐานการเขียนโปรแกรม',
                'questions': [
                    {
                        'id': 'q1',
                        'question': 'การเขียนโปรแกรมคืออะไร?',
                        'type': 'multiple_choice',
                        'options': [
                            'การสร้างคำสั่งให้คอมพิวเตอร์ทำงาน',
                            'การเล่นเกมคอมพิวเตอร์',
                            'การใช้โซเชียลมีเดีย',
                            'การดูวิดีโอ'
                        ]
                    }
                ]
            },
            'learn': {
                'title': 'เริ่มเรียน: พื้นฐานการเขียนโปรแกรม',
                'sections': [
                    {
                        'title': 'แนวคิดพื้นฐาน',
                        'content': 'การเขียนโปรแกรมเป็นกระบวนการสร้างคำสั่งให้คอมพิวเตอร์ทำงานตามที่เราต้องการ'
                    }
                ]
            },
            'posttest': {
                'title': 'แบบทดสอบหลังเรียน: พื้นฐานการเขียนโปรแกรม',
                'questions': [
                    {
                        'id': 'q1',
                        'question': 'อธิบายแนวคิดหลักของการเขียนโปรแกรม',
                        'type': 'essay'
                    }
                ]
            }
        },
        'topic2': {
            'pretest': {
                'title': 'แบบทดสอบก่อนเรียน: โครงสร้างข้อมูลและอัลกอริทึม',
                'questions': []
            },
            'learn': {
                'title': 'เริ่มเรียน: โครงสร้างข้อมูลและอัลกอริทึม',
                'sections': []
            },
            'posttest': {
                'title': 'แบบทดสอบหลังเรียน: โครงสร้างข้อมูลและอัลกอริทึม',
                'questions': []
            }
        },
        'topic3': {
            'pretest': {
                'title': 'แบบทดสอบก่อนเรียน: การพัฒนาเว็บไซต์',
                'questions': []
            },
            'learn': {
                'title': 'เริ่มเรียน: การพัฒนาเว็บไซต์',
                'sections': []
            },
            'posttest': {
                'title': 'แบบทดสอบหลังเรียน: การพัฒนาเว็บไซต์',
                'questions': []
            }
        }
    }

def save_answer(answer_key, answers):
    """บันทึกคำตอบของผู้เรียน"""
    try:
        answers_file = 'answers_data.json'
        answers_data = {}
        
        if os.path.exists(answers_file):
            with open(answers_file, 'r', encoding='utf-8') as f:
                answers_data = json.load(f)
        
        answers_data[answer_key] = {
            'answers': answers,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(answers_file, 'w', encoding='utf-8') as f:
            json.dump(answers_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Error saving answers: {e}")

def calculate_score(topic_id, step_id, answers):
    """คำนวณคะแนน (ตัวอย่าง)"""
    # ในการใช้งานจริง ควรมีเฉลยและวิธีการคำนวณคะแนนที่ซับซ้อนกว่านี้
    if step_id in ['pretest', 'posttest']:
        return len([ans for ans in answers.values() if ans]) * 20  # 20 คะแนนต่อข้อ
    return 100  # สำหรับขั้นตอนการเรียน


# ฟังก์ชันดึง follow-ups
def get_all_followups():
    conn = sqlite3.connect("patients.db")
    conn.row_factory = sqlite3.Row
    followups = conn.execute("SELECT * FROM patients ORDER BY followup_date DESC").fetchall()
    conn.close()
    return [dict(f) for f in followups]

@app.route('/video_call', methods=['GET', 'POST'])
def video_call():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        HN = request.form['HN'] 
        followup_text = request.form['followup_text']
        followup_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect("patients.db") as conn:
            conn.execute('''
                INSERT INTO patients (patient_name, HN, followup_text, followup_date)
                VALUES (?, ?, ?, ?)
            ''', (patient_name, HN, followup_text, followup_date))
            conn.commit()

        return redirect(url_for('video_call'))

    followups = get_all_followups()
    return render_template('video_call.html', followups=followups)


@app.route('/api/patients', methods=['GET'])
def get_patients():
    data = [
        {"id": 1, "name": "John Doe", "HN": "12345"},
        {"id": 2, "name": "Jane Smith", "HN": "67890"}
    ]
    return jsonify(data)


""" @app.route('/api/start-call', methods=['POST'])
def start_call():
    patient_id = request.json.get('patient_id')
    patient = next((p for p in patients if p['id'] == patient_id), None)

    if patient:
        return jsonify({
            "success": True,
            "message": f"เริ่มการโทรกับ {patient['name']}",
            "call_id": f"call_{patient_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        })
    else:
        return jsonify({
            "success": False,
            "message": "ไม่พบข้อมูลผู้ป่วย"
        }) """

""" @app.route('/api/end-call', methods=['POST'])
def end_call():
    call_id = request.json.get('call_id')
    return jsonify({
        "success": True,
        "message": "จบการโทรเรียบร้อย",
        "call_id": call_id
    }) """

if __name__ == '__main__':
    # เตรียมฐานข้อมูลสำหรับผู้ใช้งานและอุปกรณ์
    init_users_db()
    init_patients_db()
    init_learn_db()

    # เริ่มต้นเซิร์ฟเวอร์ Flask
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
