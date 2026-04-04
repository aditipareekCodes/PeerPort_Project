import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'peerport_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('peerport.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# AUTH & AUTO-REGISTRATION
# ==========================================
# ==========================================
# AUTH & AUTO-REGISTRATION
# ==========================================
@app.route('/')
def home():
    # This renders your beautiful landing page instead of redirecting
    return render_template('index.html')

@app.route('/index.html')
def index_file():
    # This handles the "Return to Home" button click specifically
    return render_template('index.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    # 1. Grab credentials from form
    moodle_id = request.form.get('moodle_id', '').strip()
    password = request.form.get('password', '').strip()
    
    # 2. Strict 8-Digit Validation (Server-side safety)
    if len(moodle_id) != 8 or len(password) != 8:
        return """
        <div style="background:#050505; color:white; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; font-family:sans-serif;">
            <h1 style="color:#ff3366;">❌ VALIDATION FAILED</h1>
            <p>Both Moodle ID and Password must be exactly <strong>8 digits</strong>.</p>
            <a href="/login.html" style="color:#00e5ff; text-decoration:none; border:1px solid #00e5ff; padding:10px 20px; border-radius:5px;">Try Again</a>
        </div>
        """, 400

    session['user_id'] = moodle_id
    conn = get_db_connection()
    
    # Check if user exists
    user = conn.execute('SELECT full_name FROM users WHERE moodle_id = ?', (moodle_id,)).fetchone()
    
    # AUTO-REGISTER (Keep this for easy testing/grading)
    if not user:
        default_name = f"Student {moodle_id}"
        conn.execute('''
            INSERT INTO users (moodle_id, full_name, phone, privacy_mode, profile_pic, seller_rating, rating_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (moodle_id, default_name, 'Not Provided', 'Public', 'default_avatar.png', 5.0, 1))
        conn.commit()
        session['user_name'] = default_name
    else:
        session['user_name'] = user['full_name']
        
    conn.close()
    return redirect('/dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login.html')

@app.route('/dashboard.html')
def dashboard():
    if 'user_id' not in session: return redirect('/login.html')
    return render_template('dashboard.html', user_name=session.get('user_name'))

# ==========================================
# SETTINGS & PROFILE
# ==========================================
@app.route('/settings.html', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    
    if request.method == 'POST':
        new_name = request.form['full_name']
        new_phone = request.form['phone']
        privacy = request.form['privacy_mode']
        file = request.files.get('profile_pic')
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute('UPDATE users SET full_name=?, phone=?, privacy_mode=?, profile_pic=? WHERE moodle_id=?',
                         (new_name, new_phone, privacy, filename, session['user_id']))
        else:
            conn.execute('UPDATE users SET full_name=?, phone=?, privacy_mode=? WHERE moodle_id=?',
                         (new_name, new_phone, privacy, session['user_id']))
        conn.commit()
        session['user_name'] = new_name 
        return redirect('/settings.html?success=true')

    user_data = conn.execute('SELECT * FROM users WHERE moodle_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('settings.html', user=user_data, success=(request.args.get('success') == 'true'))

# ==========================================
# MARKETPLACE (BUY/SELL/DETAILS)
# ==========================================
@app.route('/sell.html', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session: return redirect('/login.html')
    if request.method == 'POST':
        title, desc = request.form['title'], request.form['description']
        orig_p, sell_p = request.form['original_price'], request.form['price']
        cond, cat, sem = request.form['condition'], request.form['category'], request.form['semester']
        
        files = request.files.getlist('images')
        filenames = []
        for file in files[:5]:
            if file and file.filename != '':
                fn = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
                filenames.append(fn)
        
        img_str = ",".join(filenames) if filenames else 'default_book.png'
        conn = get_db_connection()
        conn.execute('''INSERT INTO listings (seller_id, title, description, original_price, selling_price, condition, category, semester, image_file, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available')''', 
                     (session['user_id'], title, desc, orig_p, sell_p, cond, cat, sem, img_str))
        conn.commit()
        conn.close()
        return redirect('/purchases.html')
    return render_template('sell.html', user_name=session.get('user_name'))

@app.route('/buy.html')
def buy():
    if 'user_id' not in session: return redirect('/login.html')
    search = request.args.get('search', '').strip().lower()
    cat, sem, sort = request.args.get('category', 'All'), request.args.get('semester', 'Any'), request.args.get('sort', 'newest')

    sql = "SELECT l.*, u.full_name as seller_name FROM listings l JOIN users u ON l.seller_id = u.moodle_id WHERE l.status = 'Available'"
    params = []
    if search: sql += " AND LOWER(l.title) LIKE ?"; params.append(f'%{search}%')
    if cat != 'All': sql += " AND l.category = ?"; params.append(cat)
    if sem != 'Any': sql += " AND l.semester = ?"; params.append(sem)
    
    if sort == 'price_low': sql += " ORDER BY l.selling_price ASC"
    elif sort == 'price_high': sql += " ORDER BY l.selling_price DESC"
    else: sql += " ORDER BY l.item_id DESC"

    conn = get_db_connection()
    items = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('buy.html', items=items, search=search, current_category=cat, current_semester=sem, current_sort=sort)

@app.route('/item/<int:item_id>')
def view_item(item_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    item = conn.execute('SELECT l.*, u.full_name as seller_name, u.seller_rating, u.rating_count, u.profile_pic FROM listings l JOIN users u ON l.seller_id = u.moodle_id WHERE l.item_id = ?', (item_id,)).fetchone()
    conn.close()
    return render_template('item.html', item=item) if item else ("Not Found", 404)

# ==========================================
# TRANSACTIONS & CHAT
# ==========================================
@app.route('/request_item/<int:item_id>', methods=['POST'])
def request_item(item_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    
    item = conn.execute('SELECT seller_id FROM listings WHERE item_id = ?', (item_id,)).fetchone()
    
    # FIX: Wrap both in str() to ensure they match even if types differ
    if str(item['seller_id']) == str(session['user_id']):
        conn.close()
        return "❌ Access Denied: You cannot request your own asset. Log in as a different student to test.", 403
    
    # Create the transaction
    conn.execute('INSERT INTO transactions (item_id, buyer_id, seller_id) VALUES (?, ?, ?)', 
                 (item_id, session['user_id'], item['seller_id']))
    
    # Hide from marketplace
    conn.execute("UPDATE listings SET status = 'Pending' WHERE item_id = ?", (item_id,))
    
    conn.commit()
    conn.close()
    return redirect('/purchases.html')

@app.route('/purchases.html')
def purchases():
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    user = str(session['user_id']) # Force to string for comparison
    
    # Using LEFT JOIN so it doesn't disappear if a user profile is missing
    buying = conn.execute('''
        SELECT t.tx_id, l.title, l.selling_price, IFNULL(u.full_name, 'Other Student') as other_party 
        FROM transactions t 
        JOIN listings l ON t.item_id = l.item_id 
        LEFT JOIN users u ON t.seller_id = u.moodle_id 
        WHERE t.buyer_id = ?''', (user,)).fetchall()
    
    selling = conn.execute('''
        SELECT t.tx_id, l.title, l.selling_price, IFNULL(u.full_name, 'Other Student') as other_party 
        FROM transactions t 
        JOIN listings l ON t.item_id = l.item_id 
        LEFT JOIN users u ON t.buyer_id = u.moodle_id 
        WHERE t.seller_id = ?''', (user,)).fetchall()
    
    conn.close()
    return render_template('purchases.html', buying=buying, selling=selling)

@app.route('/chat/<int:tx_id>', methods=['GET', 'POST'])
def chat(tx_id):
    if 'user_id' not in session: return redirect('/login.html')
    if request.method == 'POST':
        msg = request.form.get('message')
        if msg:
            conn = get_db_connection()
            conn.execute('INSERT INTO messages (tx_id, sender_id, message) VALUES (?, ?, ?)', (tx_id, session['user_id'], msg))
            conn.commit(); conn.close()
            return "Sent", 200
    return render_template('chat.html', tx_id=tx_id, current_user=session['user_id'])

@app.route('/api/chat/<int:tx_id>')
def api_chat(tx_id):
    conn = get_db_connection()
    msgs = conn.execute('SELECT m.*, u.full_name, u.profile_pic FROM messages m JOIN users u ON m.sender_id = u.moodle_id WHERE m.tx_id = ? ORDER BY m.timestamp ASC', (tx_id,)).fetchall()
    conn.close()
    return jsonify({'messages': [dict(m) for m in msgs]})

@app.route('/cancel_deal/<int:tx_id>', methods=['POST'])
def cancel_deal(tx_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    # Find the item linked to this deal
    deal = conn.execute('SELECT item_id FROM transactions WHERE tx_id = ?', (tx_id,)).fetchone()
    if deal:
        # 1. Put the item back on the market
        conn.execute("UPDATE listings SET status = 'Available' WHERE item_id = ?", (deal['item_id'],))
        # 2. Delete the transaction record
        conn.execute("DELETE FROM transactions WHERE tx_id = ?", (tx_id,))
        # 3. Delete related chat messages
        conn.execute("DELETE FROM messages WHERE tx_id = ?", (tx_id,))
        conn.commit()
    conn.close()
    return redirect('/purchases.html')

@app.route('/mark_sold/<int:tx_id>', methods=['POST'])
def mark_sold(tx_id):
    if 'user_id' not in session: return redirect('/login.html')
    conn = get_db_connection()
    deal = conn.execute('SELECT item_id FROM transactions WHERE tx_id = ?', (tx_id,)).fetchone()
    if deal:
        # Permanently delete the item and the deal records
        conn.execute("DELETE FROM listings WHERE item_id = ?", (deal['item_id'],))
        conn.execute("DELETE FROM transactions WHERE tx_id = ?", (tx_id,))
        conn.execute("DELETE FROM messages WHERE tx_id = ?", (tx_id,))
        conn.commit()
    conn.close()
    return redirect('/purchases.html')

if __name__ == '__main__':
    app.run(debug=True)