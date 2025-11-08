from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from db_config import get_connection
from datetime import datetime
import hashlib
import random
import pandas as pd
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.before_request
def require_login():
    open_routes = ['login', 'signup', 'admin_login', 'admin_signup', 'static', 'welcome',
                   'user_forgot_password', 'user_reset_password',
                   'admin_forgot_password', 'admin_reset_password']
    if request.endpoint not in open_routes and 'user' not in session and 'admin' not in session:
        return redirect(url_for('login'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/user/forgot_password', methods=['GET', 'POST'])
def user_forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            otp = random.randint(100000, 999999)
            session['reset_username'] = username
            session['reset_otp'] = str(otp)
            flash(f"Your OTP is: {otp}", "info")
            return redirect(url_for('user_reset_password'))
        else:
            flash("Username not found!", "danger")
    return render_template('user_forgot_password.html')

@app.route('/user/reset_password', methods=['GET', 'POST'])
def user_reset_password():
    if 'reset_username' not in session or 'reset_otp' not in session:
        flash("Session expired. Try again.", "danger")
        return redirect(url_for('user_forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form['otp']
        new_password = hash_password(request.form['new_password'])

        if entered_otp == session.get('reset_otp'):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = %s WHERE username = %s",
                           (new_password, session.get('reset_username')))
            conn.commit()
            conn.close()
            session.pop('reset_username', None)
            session.pop('reset_otp', None)
            flash("Password reset successful. Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid OTP. Please try again.", "danger")
    return render_template('user_reset_password.html')

@app.route('/admin/forgot_password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            otp = random.randint(100000, 999999)
            session['admin_reset_username'] = username
            session['admin_reset_otp'] = str(otp)
            flash(f"Your OTP is: {otp}", "info")
            return redirect(url_for('admin_reset_password'))
        else:
            flash("Admin username not found!", "danger")
    return render_template('admin_forgot_password.html')

@app.route('/admin/reset_password', methods=['GET', 'POST'])
def admin_reset_password():
    if 'admin_reset_username' not in session or 'admin_reset_otp' not in session:
        flash("Session expired. Try again.", "danger")
        return redirect(url_for('admin_forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form['otp']
        new_password = hash_password(request.form['new_password'])

        if entered_otp == session.get('admin_reset_otp'):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE admins SET password = %s WHERE username = %s",
                           (new_password, session.get('admin_reset_username')))
            conn.commit()
            conn.close()
            session.pop('admin_reset_username', None)
            session.pop('admin_reset_otp', None)
            flash("Password reset successful. Please login.", "success")
            return redirect(url_for('admin_login'))
        else:
            flash("Invalid OTP. Please try again.", "danger")
    return render_template('admin_reset_password.html')


@app.route('/')
def index():
    filter_days = request.args.get('filter_days')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if filter_days == '7':
        cursor.execute("SELECT * FROM cases WHERE sent_date >= CURDATE() - INTERVAL 7 DAY")
    elif filter_days == '30':
        cursor.execute("SELECT * FROM cases WHERE sent_date >= CURDATE() - INTERVAL 30 DAY")
    else:
        cursor.execute("SELECT * FROM cases")

    cases = cursor.fetchall()

    for case in cases:
        for field in ['default_date', 'received_date', 'co6_date', 'sent_date']:
            if case.get(field) and not isinstance(case[field], datetime):
                case[field] = datetime.combine(case[field], datetime.min.time())

        # No. of Days with Accounts
        if case.get('default_date'):
            case['no_of_days_with_accounts'] = f"{abs((datetime.now() - case['default_date']).days)} days"

        if case.get('co6_date') and case.get('sent_date'):
            delta = case['sent_date'] - case['co6_date']
            case['no_of_days_with_accounts'] = f"{abs(delta.days)} days"

        # No. of Days with Stores
        if case.get('received') and case.get('received_date') and case.get('sent_date'):
            store_days = (case['received_date'] - case['sent_date']).days
            case['no_of_days_with_stores'] = f"{store_days} days"
        else:
            case['no_of_days_with_stores'] = ''

    conn.close()
    return render_template('index.html', cases=cases, filter_days=filter_days)

@app.route('/add', methods=['POST'])
def add_case():
    case_no = request.form['case_no']
    po_no = request.form['po_no']
    r_note_no = request.form['r_note_no']
    subject = request.form['subject']
    name = request.form['name']
    sent_to = request.form['sent_to']
    sent_date = request.form['sent_date']
    co6_date = request.form.get('co6_date') or None
    default_date = datetime.now().date()

    no_of_days_with_accounts = None
    if co6_date and sent_date:
        d1 = datetime.strptime(co6_date, "%Y-%m-%d")
        d2 = datetime.strptime(sent_date, "%Y-%m-%d")
        delta = d2 - d1
        no_of_days_with_accounts = f"{abs(delta.days)} days"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cases 
        (case_no, po_no, r_note_no, subject, name, sent_to, sent_date, co6_date, default_date, no_of_days_with_accounts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (case_no, po_no, r_note_no, subject, name, sent_to, sent_date, co6_date, default_date, no_of_days_with_accounts))
    conn.commit()
    conn.close()
    flash('Case added successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/received/<int:case_id>')
def mark_received(case_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case = cursor.fetchone()
    conn.close()
    return render_template('received.html', case=case)

@app.route('/confirm_received/<int:case_id>', methods=['POST'])
def confirm_received(case_id):
    now = datetime.now()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT sent_date FROM cases WHERE id = %s", (case_id,))
    case = cursor.fetchone()

    if case and case.get('sent_date'):
        sent_date = case['sent_date']
        if not isinstance(sent_date, datetime):
            sent_date = datetime.combine(sent_date, datetime.min.time())
        store_days = (now - sent_date).days
        no_of_days_with_stores = f"No. of Days with Stores: {store_days} days"
    else:
        no_of_days_with_stores = None

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cases 
        SET received = TRUE, received_date = %s, no_of_days_with_stores = %s 
        WHERE id = %s
    """, (now, no_of_days_with_stores, case_id))
    conn.commit()
    conn.close()
    flash("Case marked as received!", "success")
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = hash_password(request.form['password'])

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, full_name, email, phone) VALUES (%s, %s, %s, %s, %s)",
                           (username, password, full_name, email, phone))
            conn.commit()
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Username already exists.', 'danger')
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = hash_password(request.form['password'])

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO admins (username, password, full_name, email, phone) VALUES (%s, %s, %s, %s, %s)",
                           (username, password, full_name, email, phone))
            conn.commit()
            flash('Admin signup successful. Please login.', 'success')
            return redirect(url_for('admin_login'))
        except:
            flash('Admin username already exists.', 'danger')
        finally:
            conn.close()
    return render_template('admin_signup.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username = %s AND password = %s", (username, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['admin'] = admin['username']
            flash('Admin logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid admin credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('admin', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/delete/<int:case_id>', methods=['POST'])
def delete_case(case_id):
    if 'admin' not in session:
        flash("Only admins can delete cases.", "danger")
        return redirect(url_for('index'))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases WHERE id = %s", (case_id,))
    conn.commit()
    conn.close()
    flash("Case deleted successfully!", "info")
    return redirect(url_for('index'))

@app.route('/edit/<int:case_id>')
def edit_case(case_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case = cursor.fetchone()
    conn.close()
    return render_template('edit.html', case=case)

@app.route('/update/<int:case_id>', methods=['POST'])
def update_case(case_id):
    case_no = request.form['case_no']
    po_no = request.form['po_no']
    r_note_no = request.form['r_note_no']
    subject = request.form['subject']
    name = request.form['name']
    sent_to = request.form['sent_to']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cases 
        SET case_no = %s, po_no = %s, r_note_no = %s, subject = %s, name = %s, sent_to = %s 
        WHERE id = %s
    """, (case_no, po_no, r_note_no, subject, name, sent_to, case_id))
    conn.commit()
    conn.close()
    flash("Case updated successfully!", "success")
    return redirect(url_for('index'))

@app.route('/export/excel')
def export_excel():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cases")
    data = cursor.fetchall()
    conn.close()

    for row in data:
        for field in ['co6_date', 'sent_date', 'received_date', 'default_date']:
            if row.get(field):
                row[field] = row[field].strftime('%d-%m-%Y')
            else:
                row[field] = ''

    df = pd.DataFrame(data)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Cases')
    writer.close()
    output.seek(0)

    response = make_response(output.read())
    response.headers['Content-Disposition'] = 'attachment; filename=cases.xlsx'
    response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response

@app.route('/export/pdf')
def export_pdf():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cases")
    data = cursor.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Case Management Report", ln=True, align='C')
    pdf.ln(10)

    for case in data:
        pdf.cell(200, 10, txt=f"{case['case_no']} - {case['name']} - {case['sent_to']}", ln=True)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Disposition'] = 'attachment; filename=cases.pdf'
    response.headers['Content-type'] = 'application/pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)
