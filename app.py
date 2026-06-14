import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Booking
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'latitude-zero-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'latitude_zero.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin panel.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===== Admin Auth Routes =====
@app.route('/admin/')
@login_required
def admin_dashboard():
    today = date.today()
    pending_bookings = Booking.query.filter_by(status='pending').count()
    total_bookings = Booking.query.count()
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    total_users = User.query.count()
    return render_template('dashboard.html',
                           pending=pending_bookings,
                           total=total_bookings,
                           recent=recent_bookings,
                           total_users=total_users,
                           now=today)

@app.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/admin/logout/')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

# ===== Booking Management =====
@app.route('/admin/bookings/')
@login_required
def admin_bookings():
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    query = query.order_by(Booking.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('bookings.html',
                           bookings=pagination.items,
                           pagination=pagination,
                           status_filter=status_filter)

@app.route('/admin/bookings/<int:booking_id>/', methods=['GET', 'POST'])
@login_required
def admin_booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'approve':
            booking.status = 'confirmed'
        elif action == 'reject':
            booking.status = 'rejected'
        elif action == 'archive':
            booking.status = 'archived'
        db.session.commit()
        flash(f'Booking #{booking.id} updated to {booking.status}.', 'success')
        return redirect(url_for('admin_bookings'))
    return render_template('booking_detail.html', booking=booking)

@app.route('/api/bookings/', methods=['POST'])
def api_create_booking():
    try:
        data = request.get_json() or {}
        required = ['checkin', 'checkout', 'name', 'email']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing {field}'}), 400

        booking = Booking(
            checkin=datetime.strptime(data['checkin'], '%Y-%m-%d').date(),
            checkout=datetime.strptime(data['checkout'], '%Y-%m-%d').date(),
            guests=data.get('guests', '2'),
            room=data.get('room', 'Standard Room'),
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', ''),
            requests=data.get('requests', ''),
            source='api'
        )
        db.session.add(booking)
        db.session.commit()
        return jsonify({'success': True, 'booking_id': booking.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ===== User Management =====
@app.route('/admin/users/')
@login_required
def admin_users():
    if not current_user.is_superuser:
        flash('Access denied. Superuser only.', 'error')
        return redirect(url_for('admin_dashboard'))
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)

@app.route('/admin/users/create/', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if not current_user.is_superuser:
        flash('Access denied. Superuser only.', 'error')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        is_superuser = request.form.get('is_superuser') == 'on'

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
        elif not password:
            flash('Password is required.', 'error')
        else:
            user = User(username=username, email=email, is_superuser=is_superuser)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'User {username} created successfully.', 'success')
            return redirect(url_for('admin_users'))
    return render_template('user_edit.html', user=None)

@app.route('/admin/users/<int:user_id>/edit/', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_superuser:
        flash('Access denied. Superuser only.', 'error')
        return redirect(url_for('admin_dashboard'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        is_superuser = request.form.get('is_superuser') == 'on'
        is_active = request.form.get('is_active') == 'on'

        if email != user.email and User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
        else:
            user.email = email
            user.is_superuser = is_superuser
            user.is_active = is_active
            if password:
                user.set_password(password)
            db.session.commit()
            flash(f'User {user.username} updated.', 'success')
            return redirect(url_for('admin_users'))
    return render_template('user_edit.html', user=user)

@app.route('/admin/users/<int:user_id>/delete/', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_superuser:
        flash('Access denied. Superuser only.', 'error')
        return redirect(url_for('admin_dashboard'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted.', 'success')
    return redirect(url_for('admin_users'))

# ===== Stats API =====
@app.route('/admin/api/stats/')
@login_required
def admin_stats():
    today = date.today()
    month_start = today.replace(day=1)
    this_month = Booking.query.filter(Booking.created_at >= month_start).count()
    return jsonify({
        'total_bookings': Booking.query.count(),
        'pending_bookings': Booking.query.filter_by(status='pending').count(),
        'confirmed_bookings': Booking.query.filter_by(status='confirmed').count(),
        'this_month': this_month,
        'total_users': User.query.count()
    })

# ===== Static File Serving =====
@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/styles.css')
def serve_styles():
    return send_from_directory(BASE_DIR, 'styles.css')

@app.route('/script.js')
def serve_script():
    return send_from_directory(BASE_DIR, 'script.js')

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'images'), filename)

@app.route('/pages/<path:filename>')
def serve_pages(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'pages'), filename)

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.endswith('.html'):
        return send_from_directory(BASE_DIR, filename)
    elif filename.endswith('.css'):
        return send_from_directory(BASE_DIR, filename)
    elif filename.endswith('.js'):
        return send_from_directory(BASE_DIR, filename)
    return send_from_directory(BASE_DIR, filename)

# ===== Initialize Database =====
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            superuser = User(username='admin', email='admin@latitudezero.ug', is_superuser=True)
            superuser.set_password('latitude2026')
            db.session.add(superuser)
            db.session.commit()
            print('Superuser created: admin / latitude2026')
        else:
            print('Admin user already exists.')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)