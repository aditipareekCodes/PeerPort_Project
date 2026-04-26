import os
import secrets
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, jsonify,flash
from flask_mail import Mail
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from functools import wraps
import random
import time
import re
from flask_mail import (
    Mail,
    Message
)

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'fallback_dev_key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
bcrypt = Bcrypt(app)

# --- Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
mail = Mail(app)

DATABASE = 'peerport.db'

# --- Database Connection ---
def get_db_connection():
    # Connects to the SQLite relational database 
    conn = sqlite3.connect('peerport.db')
    # Critical: Allows accessing columns by name (e.g., row['email'])
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            moodle_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT,
            department TEXT,
            year TEXT, 
            privacy_mode TEXT DEFAULT 'Email Only',
            profile_pic TEXT DEFAULT 'default_avatar.png',
            seller_rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 1,
            buyer_rating REAL DEFAULT 5.0,
            buyer_rating_count INTEGER DEFAULT 1
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            original_price REAL,
            selling_price REAL NOT NULL,
            condition TEXT,
            category TEXT,
            semester TEXT,
            image_file TEXT,
            status TEXT DEFAULT 'Available',
            product_rating REAL DEFAULT 5.0,
            product_rating_count INTEGER DEFAULT 1,
            FOREIGN KEY (seller_id) REFERENCES users (moodle_id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            buyer_id TEXT,
            seller_id TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (item_id) REFERENCES listings (item_id),
            FOREIGN KEY (buyer_id) REFERENCES users (moodle_id),
            FOREIGN KEY (seller_id) REFERENCES users (moodle_id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id INTEGER,
            sender_id TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tx_id) REFERENCES transactions (tx_id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contact_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id INTEGER,
            reviewer_id TEXT,
            reviewed_id TEXT,
            item_id INTEGER,
            stars INTEGER,
            comment TEXT,
            FOREIGN KEY (tx_id) REFERENCES transactions(tx_id)
    )
    ''')
                 
    conn.commit()
    conn.close()

# ==========================================
# AUTHENTICATION
# ==========================================
@app.route('/')
@app.route('/index.html')
def home():
    return render_template('index.html')

# ---- Login Required Decorator ----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

# ---- Security: Official Email Check ----
def is_college_email(email):
    # Enforces the requirement for verified college addresses 
    return email.lower().endswith('@apsit.edu.in')

# ---- Login Route ----
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        
        # Using .get() prevents crashes if fields are missing
        moodle_id = request.form.get('moodle_id', '').strip()
        password = request.form.get('password', '').strip()

        # 1. ADMIN BYPASS
        if moodle_id == os.getenv('ADMIN_ID') and password == os.getenv('ADMIN_PASSWORD'):
            session['user_id'] = moodle_id
            session['user_name'] = os.getenv('ADMIN_NAME', 'Admin')
            session['is_admin'] = True
            return redirect('/admin_dashboard')
        
        
        # 2. VALIDATION: Check Moodle ID Length
        if len(moodle_id) != 8:
            flash("❌ Moodle ID must be exactly 8 digits", "danger")
            return render_template('login.html')

        # 3. DATABASE CHECK
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE moodle_id = ?', (moodle_id,)).fetchone()
        conn.close()

        # Secure password verification using Bcrypt 
        if user:
            print(f"DEBUG: Found user {moodle_id} in DB") # Check terminal
            if bcrypt.check_password_hash(user['password_hash'], password):
                print("DEBUG: Password matched!") # Check terminal
                session['user_id'] = user['moodle_id']
                session['user_name'] = user['full_name']
                return redirect('/dashboard.html')
            else:
                print("DEBUG: Password mismatch") # Check terminal
        else:
            print(f"DEBUG: User {moodle_id} not found") # Check terminal
            
        flash('Invalid Moodle ID or Password.', 'danger')

    # If we are here, it's a 'GET' or a failed 'POST'
    return render_template('login.html')

# -------------------------------
# REGISTER ROUTE (FIXED)
# -------------------------------

@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        department = request.form.get('department')
        year = request.form.get('year')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        otp_received = request.form.get('otp_code')

        # ✅ STRICT EMAIL VALIDATION
        if not re.fullmatch(r'\d{8}@apsit\.edu\.in', email):
            flash('❌ Use valid college email (8digit@apsit.edu.in)', 'danger')
            return render_template('login.html')

        moodle_id = email.split('@')[0]

        # Block admin
        if moodle_id == os.getenv('ADMIN_ID'):
            flash('❌ This ID cannot be registered.', 'danger')
            return render_template('login.html')
        
        # PASSWORD VALIDATION
        if len(password) < 8:
            flash('❌ Password must be at least 8 characters.', 'danger')
            return render_template('login.html')
        if not re.search(r'[A-Z]', password):
            flash('❌ Must contain uppercase.', 'danger')
            return render_template('login.html')
        if not re.search(r'[a-z]', password):
            flash('❌ Must contain lowercase.', 'danger')
            return render_template('login.html')
        if not re.search(r'[0-9]', password):
            flash('❌ Must contain number.', 'danger')
            return render_template('login.html')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('❌ Must contain special character.', 'danger')
            return render_template('login.html')

        # OTP CHECK
        stored_otp = session.get('otp_code')
        stored_email = session.get('otp_email')
        otp_expiry = session.get('otp_expiry')

        if not stored_otp or not otp_received:
            flash('❌ Request OTP first.', 'danger')
            return render_template('login.html')

        if stored_email != email:
            flash('❌ OTP sent to different email.', 'danger')
            return render_template('login.html')

        if time.time() > otp_expiry:
            session.pop('otp_code', None)
            flash('❌ OTP expired.', 'danger')
            return render_template('login.html')

        if otp_received != stored_otp:
            flash('❌ Invalid OTP.', 'danger')
            return render_template('login.html')

        # CLEAR OTP
        session.pop('otp_code', None)
        session.pop('otp_email', None)
        session.pop('otp_expiry', None)

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        try:
            conn.execute(
                 '''INSERT INTO users 
                (moodle_id, full_name, email, phone, password_hash, department, year) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (moodle_id, full_name, email, phone, hashed_pw, department, year)
            )
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect('/login.html')
        except sqlite3.IntegrityError:
            flash('Account already exists.', 'danger')
        finally:
            conn.close()

    return render_template('login.html')
 

# ---- Dashboard & Logout ----
@app.route('/dashboard.html')
@login_required
def dashboard():
    # Displays personalized welcome and user rating summary
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE moodle_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('dashboard.html', user_name=session.get('user_name'), user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login.html')





# -------------------------------
# SEND OTP (IMPROVED)
# -------------------------------
@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = request.json.get('email', '').strip().lower()

    # ✅ STRICT VALIDATION
    if not re.fullmatch(r'\d{8}@apsit\.edu\.in', email):
        return jsonify({'success': False, 'message': 'Use valid college email'})

    moodle_id = email.split('@')[0]

    conn = get_db_connection()
    existing = conn.execute(
        'SELECT moodle_id FROM users WHERE moodle_id = ?',
        (moodle_id,)
    ).fetchone()
    conn.close()

    if existing:
        return jsonify({'success': False, 'message': 'Account already exists'})

    otp = str(random.randint(100000, 999999))
    session['otp_code'] = otp
    session['otp_email'] = email
    session['otp_expiry'] = time.time() + 300

    try:
        msg = Message(
            subject='PeerPort OTP',
            recipients=[email]
        )
        msg.body = f"""Hello!

Welcome to PeerPort — the official student marketplace for APSIT.

You are receiving this email because someone used this address
to register a new PeerPort account. To complete your registration,
please verify your identity using the OTP below.

Your verification OTP is:

        {otp}

This code is valid for 5 minutes only. Enter it on the
registration page to activate your account.

Please do not share this OTP with anyone — PeerPort staff
will never ask for your verification code.

If you did not attempt to register on PeerPort, please
ignore this email. No account will be created without
entering this code.

— The PeerPort Team
Built exclusively for APSIT students
"""
        
        mail.send(msg)

        print("OTP SENT:", otp)  # debug

        return jsonify({'success': True})

    except Exception as e:
        print("EMAIL ERROR:", e)  # 🔥 IMPORTANT DEBUG
        return jsonify({'success': False, 'message': 'Email failed'})
    

# ---- Verify Reset OTP Route ----
@app.route('/verify-reset-otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp_code', '').strip()
        stored_otp = session.get('reset_otp')
        reset_expiry = session.get('reset_expiry')

        if not stored_otp:
            flash('❌ No OTP was requested. Please start again.', 'danger')
            return redirect('/forgot-password')

        if time.time() > reset_expiry:
            session.pop('reset_otp', None)
            session.pop('reset_email', None)
            session.pop('reset_expiry', None)
            flash('❌ OTP has expired. Please request a new one.', 'danger')
            return redirect('/forgot-password')

        if entered_otp != stored_otp:
            flash('❌ Incorrect OTP. Please try again.', 'danger')
            return render_template('verify_reset_otp.html')

        # OTP correct — allow password reset
        session['reset_verified'] = True
        return redirect('/reset-password')

    return render_template('verify_reset_otp.html')


# ---- Forgot Password Route ----
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email.endswith('@apsit.edu.in'):
            flash('❌ Only @apsit.edu.in emails are allowed.', 'danger')
            return render_template('forgot_password.html')

        moodle_id = email.split('@')[0]
        if not moodle_id.isdigit() or len(moodle_id) != 8:
            flash('❌ Invalid email format.', 'danger')
            return render_template('forgot_password.html')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_email'] = email
            session['reset_expiry'] = time.time() + 900  # 15 minutes

            try:
                msg = Message(
                    subject='PeerPort — Password Reset OTP',
                    recipients=[email]
                )
                msg.body = f"""Hello {user['full_name']},

We received a request to reset the password for your PeerPort account
associated with this email: {email}

Your password reset OTP is:

        {otp}

This code is valid for 15 minutes only. Please do not share it
with anyone — PeerPort staff will never ask for your OTP.

If you did not request a password reset, you can safely ignore
this email. Your account remains secure and no changes have been made.

Need help? Reach out to us through the Contact page on PeerPort.

— The PeerPort Team
  Built exclusively for APSIT students."""
                mail.send(msg)
            except Exception:
                flash('❌ Failed to send OTP email. Please try again.', 'danger')
                return render_template('forgot_password.html')

        # Always show this — don't reveal if email exists
        flash('✅ If that email is registered, a 6-digit OTP has been sent to it.', 'success')
        return redirect('/verify-reset-otp')

    return render_template('forgot_password.html')
    



# ---- Reset Password Route ----
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Must have verified OTP first
    if not session.get('reset_verified'):
        flash('❌ Please verify your OTP first.', 'danger')
        return redirect('/forgot-password')

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        reset_email = session.get('reset_email')

        if new_password != confirm_password:
            flash('❌ Passwords do not match.', 'danger')
            return render_template('reset_password.html')
        if len(new_password) < 8:
            flash('❌ Password must be at least 8 characters.', 'danger')
            return render_template('reset_password.html')
        if not re.search(r'[A-Z]', new_password):
            flash('❌ Must contain at least one uppercase letter.', 'danger')
            return render_template('reset_password.html')
        if not re.search(r'[a-z]', new_password):
            flash('❌ Must contain at least one lowercase letter.', 'danger')
            return render_template('reset_password.html')
        if not re.search(r'[0-9]', new_password):
            flash('❌ Must contain at least one number.', 'danger')
            return render_template('reset_password.html')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            flash('❌ Must contain at least one special character.', 'danger')
            return render_template('reset_password.html')

        hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
        conn = get_db_connection()
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (hashed_pw, reset_email))
        conn.commit()
        conn.close()

        # Clear all reset session data
        session.pop('reset_otp', None)
        session.pop('reset_email', None)
        session.pop('reset_expiry', None)
        session.pop('reset_verified', None)

        flash('✅ Password reset successful! Please log in with your new password.', 'success')
        return redirect('/login.html')

    return render_template('reset_password.html')

# ==========================================
# MARKETPLACE (BUY/SELL)
# ==========================================
@app.route('/sell.html', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session: return redirect('/login.html')

    if request.method == 'POST':
        # 1. Capture text fields from the form
        title = request.form.get('title')
        desc = request.form.get('description')
        original_p = request.form.get('original_price')
        selling_p = request.form.get('price') # In your HTML this was name="price"
        item_condition = request.form.get('condition')
        cat = request.form.get('category')
        sem = request.form.get('semester')

        # 2. Handle Multiple Image Uploads
        files = request.files.getlist('images') 
        filenames = []

        for file in files[:5]:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filenames.append(filename)

        # --- THE FIX: STOP THE UPLOAD IF NO IMAGES ---
        if not filenames:
            # You can redirect back with an error or just return a message
            return "Error: You must upload at least one image to list an item.", 400

        # 3. Create the image string or use default
        img_str = ",".join(filenames) 


        # 4. Database Insertion
        conn = get_db_connection()
        conn.execute('''INSERT INTO listings 
                        (seller_id, title, description, original_price, selling_price, condition, category, semester, image_file)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (session['user_id'], title, desc, original_p, selling_p, item_condition, cat, sem, img_str))
        conn.commit()
        conn.close()
        
        return redirect('/buy.html')
        
    return render_template('sell.html')

@app.route('/buy.html')
def buy():
    if 'user_id' not in session: return redirect('/login.html')

    search = request.args.get('search', '').strip().lower()
    cat = request.args.get('category', 'All')
    sem = request.args.get('semester', 'Any')
    sort = request.args.get('sort', 'newest')

    sql = "SELECT l.*, u.full_name as seller_name, u.seller_rating as rating FROM listings l JOIN users u ON l.seller_id = u.moodle_id WHERE l.status = 'Available'"
    params = []

    if search:
        sql += " AND LOWER(l.title) LIKE ?"
        params.append(f'%{search}%')
    if cat != 'All':
        sql += " AND l.category = ?"
        params.append(cat)
    if sem != 'Any':
        sql += " AND l.semester = ?"
        params.append(sem)

    if sort == 'newest':
        sql += " ORDER BY l.item_id DESC"
    elif sort == 'price':
        sql += " ORDER BY l.selling_price ASC"
    elif sort == 'discount':
        sql += " ORDER BY CASE WHEN l.original_price > l.selling_price THEN (l.original_price - l.selling_price) / l.original_price ELSE 0 END DESC"

    conn = get_db_connection()
    items = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('buy.html', items=items, current_category=cat, current_semester=sem, current_sort=sort)

@app.route('/item/<int:item_id>')
def view_item(item_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    item = conn.execute(
        'SELECT l.*, u.full_name as seller_name, u.seller_rating, u.profile_pic, u.email as seller_email, u.phone as seller_phone, u.privacy_mode '
        'FROM listings l JOIN users u ON l.seller_id = u.moodle_id WHERE l.item_id = ?',
        (item_id,)
    ).fetchone()
    conn.close()
    return render_template('item.html', item=item, session_user_id=session.get('user_id')) if item else ("Not Found", 404)

@app.route('/report_item/<int:item_id>', methods=['POST'])
def report_item(item_id):
    if 'user_id' not in session: return redirect('/login.html')
    reason = request.form.get('reason')
    if not reason: return "Invalid reason", 400
    conn = get_db_connection()
    user = conn.execute('SELECT full_name, email FROM users WHERE moodle_id = ?', (session['user_id'],)).fetchone()
    message = f"Report for item {item_id}: {reason}"
    conn.execute('INSERT INTO contact_tickets (name, email, message) VALUES (?, ?, ?)', (user['full_name'], user['email'], message))
    conn.commit()
    conn.close()
    return redirect(url_for('view_item', item_id=item_id))

@app.route('/delete_listing/<int:item_id>', methods=['POST'])
def delete_listing(item_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    listing = conn.execute('SELECT seller_id FROM listings WHERE item_id = ?', (item_id,)).fetchone()
    if str(listing['seller_id']) != str(session['user_id']):
        conn.close()
        return "Access Denied", 403
    conn.execute('DELETE FROM listings WHERE item_id = ?', (item_id,))
    conn.commit()
    conn.close()
    return redirect('/sell.html')

# ==========================================
# DEALS & CHAT
# ==========================================
@app.route('/request_item/<int:item_id>', methods=['POST'])
def request_item(item_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    item = conn.execute('SELECT seller_id FROM listings WHERE item_id = ?', (item_id,)).fetchone()

    if str(item['seller_id']) == str(session['user_id']):
        conn.close()
        return "❌ Access Denied: You cannot buy your own item.", 403

    conn.execute(
        'INSERT INTO transactions (item_id, buyer_id, seller_id) VALUES (?, ?, ?)',
        (item_id, session['user_id'], item['seller_id'])
    )
    conn.execute("UPDATE listings SET status = 'Pending' WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect('/purchases.html')

@app.route('/purchases.html')
def purchases():
    if 'user_id' not in session: return redirect('/login.html')
    uid = str(session['user_id'])
    conn = get_db_connection()

    buying_raw = conn.execute('''
        SELECT t.tx_id, l.title, l.selling_price, l.image_file, t.status,
               u.full_name as other_party, u.email as other_email, u.phone as other_phone, u.privacy_mode as other_privacy,
               u.seller_rating as other_rating, u.rating_count as other_rating_count,
               t.seller_id, t.item_id
        FROM transactions t
        JOIN listings l ON t.item_id = l.item_id
        JOIN users u ON t.seller_id = u.moodle_id
        WHERE t.buyer_id = ?''', (uid,)).fetchall()

    try:
        selling_raw = conn.execute('''
            SELECT t.tx_id, l.title, l.selling_price, l.image_file, t.status,
                   u.full_name as other_party, u.email as other_email, u.phone as other_phone, u.privacy_mode as other_privacy,
                   u.buyer_rating as other_rating, u.buyer_rating_count as other_rating_count,
                   t.buyer_id, t.item_id
            FROM transactions t
            JOIN listings l ON t.item_id = l.item_id
            JOIN users u ON t.buyer_id = u.moodle_id
            WHERE t.seller_id = ?''', (uid,)).fetchall()
    except:
        # Fallback if buyer_rating column doesn't exist
        selling_raw = conn.execute('''
            SELECT t.tx_id, l.title, l.selling_price, l.image_file, t.status,
                   u.full_name as other_party, u.email as other_email, u.phone as other_phone, u.privacy_mode as other_privacy,
                   5.0 as other_rating, 0 as other_rating_count,
                   t.buyer_id, t.item_id
            FROM transactions t
            JOIN listings l ON t.item_id = l.item_id
            JOIN users u ON t.buyer_id = u.moodle_id
            WHERE t.seller_id = ?''', (uid,)).fetchall()

    # My available listings (not in any active transaction)
    my_listings = conn.execute('''
        SELECT * FROM listings 
        WHERE seller_id = ? AND status = 'Available'
        ORDER BY item_id DESC''', (uid,)).fetchall()

    # My sold listings
    sold_listings = conn.execute('''
        SELECT * FROM listings 
        WHERE seller_id = ? AND status = 'Sold'
        ORDER BY item_id DESC''', (uid,)).fetchall()

    # Which tx_ids has this user already rated
    rated_txs = set(
        row[0] for row in conn.execute(
            'SELECT tx_id FROM ratings WHERE reviewer_id = ?', (uid,)
        ).fetchall()
    )
    conn.close()

    buying = [dict(d) | {'rated': d['tx_id'] in rated_txs} for d in buying_raw]
    selling = [dict(d) | {'rated': d['tx_id'] in rated_txs} for d in selling_raw]

    completed_buying = [d for d in buying if d['status'] == 'Completed']
    completed_selling = [d for d in selling if d['status'] == 'Completed']

    # Debug prints
    print(f"DEBUG: User {uid} - Buying deals: {len(buying)}")
    for d in buying:
        print(f"  Buying: {d['title']} - Status: {d['status']}")
    print(f"DEBUG: Selling deals: {len(selling)}")
    for d in selling:
        print(f"  Selling: {d['title']} - Status: {d['status']}")
    print(f"DEBUG: Completed buying: {len(completed_buying)}, Completed selling: {len(completed_selling)}")

    return render_template('purchases.html',
        buying=buying, selling=selling,
        completed_buying=completed_buying,
        completed_selling=completed_selling,
        my_listings=my_listings,
        sold_listings=sold_listings
    )


@app.route('/rate_deal/<int:tx_id>', methods=['POST'])
def rate_deal(tx_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    stars = int(request.form.get('rating', 0))
    rating_type = request.form.get('type', '')
    reviewer_id = str(session['user_id'])

    if stars < 1 or stars > 5:
        return jsonify({'success': False, 'message': 'Invalid rating'})

    conn = get_db_connection()

    deal = conn.execute(
        'SELECT * FROM transactions WHERE tx_id = ? AND status = ?',
        (tx_id, 'Completed')
    ).fetchone()

    if not deal:
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid transaction'})

    # Decide who is being rated
    if rating_type == 'seller':
        reviewed_id = deal['seller_id']
    elif rating_type == 'buyer':
        reviewed_id = deal['buyer_id']
    elif rating_type == 'product':
        reviewed_id = deal['seller_id']
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid type'})

    # Prevent duplicate rating
    existing = conn.execute(
        'SELECT rating_id FROM ratings WHERE tx_id = ? AND reviewer_id = ? AND reviewed_id = ?',
        (tx_id, reviewer_id, reviewed_id)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Already rated'})

    # Insert rating
    conn.execute('''
        INSERT INTO ratings (tx_id, reviewer_id, reviewed_id, item_id, stars, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (tx_id, reviewer_id, reviewed_id, deal['item_id'], stars, rating_type))

    # Recalculate average rating
    ratings = conn.execute(
        'SELECT stars FROM ratings WHERE reviewed_id = ?',
        (reviewed_id,)
    ).fetchall()

    avg = sum(r['stars'] for r in ratings) / len(ratings)

    conn.execute('''
        UPDATE users
        SET seller_rating = ?, rating_count = ?
        WHERE moodle_id = ?
    ''', (round(avg, 1), len(ratings), reviewed_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/chat/<int:tx_id>')
def api_chat(tx_id):
    conn = get_db_connection()
    msgs = conn.execute('''
        SELECT m.*, u.full_name 
        FROM messages m 
        JOIN users u ON m.sender_id = u.moodle_id 
        WHERE m.tx_id = ? ORDER BY timestamp ASC''', (tx_id,)).fetchall()
    conn.close()
    # Convert rows to a list of dictionaries so they can be sent as JSON
    return jsonify({'messages': [dict(m) for m in msgs]})

@app.route('/chat/<int:tx_id>', methods=['GET', 'POST'])
def chat(tx_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()

    if request.method == 'POST':
        msg = request.form.get('message')
        if msg:
            conn.execute('INSERT INTO messages (tx_id, sender_id, message) VALUES (?, ?, ?)',
                         (tx_id, session['user_id'], msg))
            conn.commit()
            return "Sent", 200

    # Fetch messages AND the deal info so the page knows the item title
    deal = conn.execute('SELECT l.title FROM transactions t JOIN listings l ON t.item_id = l.item_id WHERE t.tx_id = ?', (tx_id,)).fetchone()
    messages = conn.execute('''
        SELECT m.*, u.full_name 
        FROM messages m 
        JOIN users u ON m.sender_id = u.moodle_id 
        WHERE m.tx_id = ? ORDER BY timestamp ASC''', (tx_id,)).fetchall()
    
    conn.close()
    return render_template('chat.html', tx_id=tx_id, messages=messages, deal=deal, current_user=session['user_id'])


@app.route('/complete_deal/<int:tx_id>', methods=['POST'])
def complete_deal(tx_id):
    conn = get_db_connection()
    deal = conn.execute('SELECT item_id FROM transactions WHERE tx_id = ?', (tx_id,)).fetchone()
    if deal:
        # Mark listing as Sold (This hides it from Buy page)
        conn.execute("UPDATE listings SET status = 'Sold' WHERE item_id = ?", (deal['item_id'],))
        
        # Mark the transaction itself as Completed (This keeps it in your My Deals list!)
        conn.execute("UPDATE transactions SET status = 'Completed' WHERE tx_id = ?", (tx_id,))
        
        conn.commit()
    conn.close()
    return redirect('/purchases.html')

@app.route('/cancel_request/<int:tx_id>', methods=['POST'])
def cancel_request(tx_id):
    conn = get_db_connection()
    deal = conn.execute('SELECT item_id FROM transactions WHERE tx_id = ?', (tx_id,)).fetchone()
    if deal:
        # 1. Put item back to Available
        conn.execute("UPDATE listings SET status = 'Available' WHERE item_id = ?", (deal['item_id'],))
        # 2. Delete the request
        conn.execute("DELETE FROM transactions WHERE tx_id = ?", (tx_id,))
        conn.commit()
    conn.close()
    return redirect('/purchases.html')
# ==========================================
# ADMIN & SETTINGS
# =========================================

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'): return redirect('/login.html')
    conn = get_db_connection()
    
    u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    i_count = conn.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    # Fetching closed deals (where status is 'Sold' or 'Completed')
    d_count = conn.execute("SELECT COUNT(*) FROM listings WHERE status = 'Sold'").fetchone()[0]
    
    listings = conn.execute('SELECT * FROM listings').fetchall()
    users = conn.execute('SELECT * FROM users').fetchall()
    tickets = conn.execute('SELECT * FROM contact_tickets').fetchall()
    
    conn.close()
    return render_template('admin_dashboard.html', 
                           user_count=u_count, item_count=i_count, deal_count=d_count,
                           listings=listings, users=users, tickets=tickets)


@app.route('/settings.html', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    if request.method == 'POST':
        new_name = request.form.get('full_name')
        new_phone = request.form.get('phone')
        privacy = request.form.get('privacy_mode')
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute(
                'UPDATE users SET full_name=?, phone=?, privacy_mode=?, profile_pic=? WHERE moodle_id=?',
                (new_name, new_phone, privacy, filename, session['user_id'])
            )
        else:
            conn.execute(
                'UPDATE users SET full_name=?, phone=?, privacy_mode=? WHERE moodle_id=?',
                (new_name, new_phone, privacy, session['user_id'])
            )
        conn.commit()
        session['user_name'] = new_name
        return redirect('/settings.html?success=true')
    user_data = conn.execute('SELECT * FROM users WHERE moodle_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('settings.html', user=user_data)

# ==========================================
# INFORMATIONAL PAGES
# ==========================================
@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/faqs.html')
def faqs():
    return render_template('faqs.html')

@app.route('/delete_user/<moodle_id>', methods=['POST'])
def delete_user(moodle_id):
    if not session.get('is_admin'): return redirect('/login.html')
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE moodle_id = ?', (moodle_id,))
    conn.commit()
    conn.close()
    return redirect('/admin_dashboard')

@app.route('/contact.html', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        msg = request.form.get('message')

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO contact_tickets (name, email, message) VALUES (?, ?, ?)',
            (name, email, msg)
        )
        conn.commit()
        conn.close()
        return redirect('/dashboard.html?msg_sent=true')
    return render_template('contact.html')

# Updated initialization block at the bottom of app.py
if __name__ == '__main__':
    init_db()  # Ensure DB is initialized before starting the app
    app.run(debug=True)