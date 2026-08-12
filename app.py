import os
import sys
import time
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import urlparse
from models import db, User, Booking, SiteSettings, Testimonial, Room, PageSection, GalleryImage
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def _database_uri():
    """Use DATABASE_URL (Postgres) in production; fall back to local SQLite for dev.

    Railway/Heroku hand out a 'postgres://' scheme that SQLAlchemy 2.x no longer
    accepts, so normalise it to 'postgresql://'.
    """
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url

    # No DATABASE_URL. On a managed host (Railway/Render/Heroku) SQLite lives on an
    # ephemeral disk, so every restart silently wipes bookings/content/uploads —
    # exactly the "it saved but nothing changed" trap. Fail loudly instead, unless
    # explicitly overridden with ALLOW_SQLITE=true.
    on_managed_host = any(os.environ.get(k) for k in (
        'RAILWAY_ENVIRONMENT', 'RAILWAY_PROJECT_ID', 'RAILWAY_SERVICE_ID',
        'RENDER', 'DYNO', 'FLY_APP_NAME',
    ))
    if on_managed_host and not _env_bool('ALLOW_SQLITE', False):
        raise RuntimeError(
            'DATABASE_URL is not set, but this looks like a hosted deploy where SQLite '
            'is ephemeral and loses ALL data on restart. Attach a PostgreSQL database and '
            'set DATABASE_URL (e.g. DATABASE_URL=${{Postgres.DATABASE_URL}} on Railway). '
            'To run on SQLite anyway (not recommended), set ALLOW_SQLITE=true.'
        )

    import sys
    print(
        'WARNING: DATABASE_URL is not set — falling back to local SQLite (dev only). '
        'Data will not persist across restarts on a hosted server.',
        file=sys.stderr,
    )
    return 'sqlite:///' + os.path.join(BASE_DIR, 'latitude_zero.db')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError('SECRET_KEY environment variable is not set. Aborting.')
app.config['SQLALCHEMY_DATABASE_URI'] = _database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# pool_pre_ping avoids stale-connection errors when a managed Postgres drops idle links.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# ===== Session / cookie hardening =====
# SESSION_COOKIE_SECURE must be True in production (HTTPS). Set COOKIE_SECURE=false
# only for local HTTP testing, otherwise the login cookie is never stored.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = _env_bool('COOKIE_SECURE', True)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['WTF_CSRF_TIME_LIMIT'] = None  # token valid for the life of the session

# ===== Behind a reverse proxy (nginx on a VPS, etc.) =====
# Set TRUST_PROXY=true ONLY when the app sits behind a proxy you control, so it
# reads the real client IP and https scheme from X-Forwarded-* headers. Leave it
# off otherwise, or clients could spoof those headers.
if _env_bool('TRUST_PROXY', False):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ===== CSRF protection for all admin forms =====
csrf = CSRFProtect(app)

# ===== Simple in-memory login throttle =====
# Locks an IP out after LOGIN_MAX_FAILS failures within the window. This is
# per-process (each gunicorn worker keeps its own map), which is a deliberate
# trade-off: it needs no extra infra and is ample for a small site. For a
# hard, shared limit, put a rate limiter at the reverse proxy / host layer.
LOGIN_MAX_FAILS = int(os.environ.get('LOGIN_MAX_FAILS', 8))
LOGIN_LOCK_SECONDS = int(os.environ.get('LOGIN_LOCK_SECONDS', 300))
_login_attempts = {}  # ip -> [count, first_attempt_ts]


def _login_block_seconds(ip):
    rec = _login_attempts.get(ip)
    if not rec:
        return 0
    count, first_ts = rec
    elapsed = time.time() - first_ts
    if elapsed > LOGIN_LOCK_SECONDS:
        _login_attempts.pop(ip, None)
        return 0
    if count >= LOGIN_MAX_FAILS:
        return int(LOGIN_LOCK_SECONDS - elapsed)
    return 0


def _record_login_failure(ip):
    rec = _login_attempts.get(ip)
    if not rec or (time.time() - rec[1]) > LOGIN_LOCK_SECONDS:
        _login_attempts[ip] = [1, time.time()]
    else:
        rec[0] += 1


def _clear_login_attempts(ip):
    _login_attempts.pop(ip, None)


cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', '')
)

def upload_to_cloudinary(file, folder='latitude_zero'):
    if not os.environ.get('CLOUDINARY_CLOUD_NAME'):
        raise RuntimeError('CLOUDINARY_CLOUD_NAME is not configured. Set all CLOUDINARY_* environment variables.')
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        use_filename=True,
        unique_filename=True,
        resource_type='image'
    )
    return result['secure_url']

db.init_app(app)

@app.after_request
def add_cors_headers(response):
    # Only the public read APIs are meant to be cross-origin (so the static
    # Netlify fallback copy can read live content). Admin pages stay same-origin.
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# ===== Error Handlers =====
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='Something went wrong. Please try again later.'), 500

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin panel.'

@login_manager.user_loader
def load_user(user_id):
    # Reject sessions of users who were deactivated after logging in.
    user = User.query.get(int(user_id))
    return user if (user and user.is_active) else None

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

def _is_safe_next(target):
    """Only allow same-site relative redirects to avoid an open-redirect."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith('/')


@app.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        # Key the throttle off remote_addr only. When TRUST_PROXY=true, ProxyFix
        # has already rewritten remote_addr to the real client IP from a trusted
        # proxy. Reading X-Forwarded-For directly would let an attacker rotate a
        # spoofed header and get a fresh bucket per request, defeating the lockout.
        ip = request.remote_addr or 'unknown'
        blocked_for = _login_block_seconds(ip)
        if blocked_for:
            flash(f'Too many failed attempts. Try again in {blocked_for} seconds.', 'error')
            return render_template('login.html'), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            _clear_login_attempts(ip)
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            if _is_safe_next(next_page):
                return redirect(next_page)
            return redirect(url_for('admin_dashboard'))
        _record_login_failure(ip)
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

@app.route('/admin/bookings/export/')
@login_required
def admin_export_bookings():
    import csv
    from io import StringIO
    bookings = Booking.query.filter(Booking.checkin >= date(2024, 1, 1)).order_by(Booking.created_at.desc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Room', 'Check-in', 'Check-out', 'Guests', 'Status', 'Source', 'Requests', 'Created'])
    for b in bookings:
        writer.writerow([
            b.id,
            b.name,
            b.email,
            b.phone or '',
            b.room,
            b.checkin.strftime('%Y-%m-%d') if b.checkin else '',
            b.checkout.strftime('%Y-%m-%d') if b.checkout else '',
            b.guests,
            b.status,
            b.source or '',
            b.requests or '',
            b.created_at.strftime('%Y-%m-%d %H:%M') if b.created_at else ''
        ])
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=bookings_export.csv'
    }

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
@csrf.exempt  # public endpoint called cross-origin by the booking form; no session/cookie involved
def api_create_booking():
    try:
        data = request.get_json() or {}
        required = ['checkin', 'checkout', 'name', 'email']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing {field}'}), 400

        checkin = datetime.strptime(data['checkin'], '%Y-%m-%d').date()
        checkout = datetime.strptime(data['checkout'], '%Y-%m-%d').date()
        if checkout <= checkin:
            return jsonify({'error': 'Check-out must be after check-in.'}), 400

        booking = Booking(
            checkin=checkin,
            checkout=checkout,
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
    except (ValueError, KeyError):
        return jsonify({'error': 'Invalid booking data. Check dates (YYYY-MM-DD) and required fields.'}), 400
    except Exception:
        app.logger.exception('Booking creation failed')
        db.session.rollback()
        return jsonify({'error': 'Could not save booking. Please try again.'}), 500

@app.route('/api/content/')
def api_content():
    settings = SiteSettings.get_settings()
    testimonials = Testimonial.get_active()
    rooms = Room.get_active()
    return jsonify({
        'hero': {
            'title': settings.hero_title,
            'subtitle': settings.hero_subtitle,
            'tagline': settings.hero_tagline,
            'image': settings.hero_image,
            'meta_title': settings.meta_title,
            'meta_description': settings.meta_description,
        },
        'contact': {
            'whatsapp': settings.whatsapp,
            'phone': settings.phone,
            'email': settings.email,
            'address': settings.address,
            'facebook': settings.facebook,
            'instagram': settings.instagram,
        },
        'footer': {
            'tagline': settings.footer_tagline,
            'description': settings.footer_description,
            'copyright': settings.footer_copyright,
        },
        'testimonials': [
            {
                'text': t.text,
                'author': t.author,
                'location': t.location,
                'rating': t.rating,
            } for t in testimonials
        ],
        'rooms': [
            {
                'name': r.name,
                'description': r.description,
                'price': r.price,
                'image': r.image,
                'features': r.features,
            } for r in rooms
        ]
    })

@app.route('/admin/upload/', methods=['POST'])
@login_required
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return jsonify({'error': 'File type not allowed. Use JPG, PNG, GIF, or WebP.'}), 400
    try:
        url = upload_to_cloudinary(file, 'latitude_zero/admin')
        return jsonify({'url': url})
    except Exception:
        app.logger.exception('Image upload failed')
        return jsonify({'error': 'Upload failed. Check the Cloudinary configuration and try again.'}), 500

@app.route('/api/pages/<page>/')
def api_page(page):
    sections = PageSection.get_for_page(page)
    return jsonify({
        'page': page,
        'sections': [{
            'key': s.section_key,
            'title': s.title,
            'content': s.content,
            'image': s.image,
            'meta_title': s.meta_title,
            'meta_description': s.meta_description,
        } for s in sections]
    })

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

# ===== Content Management: Settings =====
@app.route('/admin/settings/', methods=['GET', 'POST'])
@login_required
def admin_settings():
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        settings.hero_title = request.form.get('hero_title', '')
        settings.hero_subtitle = request.form.get('hero_subtitle', '')
        settings.hero_tagline = request.form.get('hero_tagline', '')
        settings.whatsapp = request.form.get('whatsapp', '')
        settings.phone = request.form.get('phone', '')
        settings.email = request.form.get('email', '')
        settings.address = request.form.get('address', '')
        settings.facebook = request.form.get('facebook', '')
        settings.instagram = request.form.get('instagram', '')
        settings.footer_tagline = request.form.get('footer_tagline', '')
        settings.footer_description = request.form.get('footer_description', '')
        settings.footer_copyright = request.form.get('footer_copyright', '')
        settings.meta_title = request.form.get('meta_title', '')
        settings.meta_description = request.form.get('meta_description', '')

        if 'hero_image' in request.files:
            file = request.files['hero_image']
            if file and file.filename:
                allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in allowed:
                    url = upload_to_cloudinary(file, 'latitude_zero/hero')
                    if url:
                        settings.hero_image = url

        db.session.commit()
        flash('Settings saved successfully.', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('settings.html', settings=settings)

# ===== Content Management: Testimonials =====
@app.route('/admin/testimonials/')
@login_required
def admin_testimonials():
    testimonials = Testimonial.query.order_by(Testimonial.sort_order, Testimonial.created_at.desc()).all()
    return render_template('testimonials.html', testimonials=testimonials)

@app.route('/admin/testimonials/create/', methods=['GET', 'POST'])
@login_required
def admin_create_testimonial():
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        author = request.form.get('author', '').strip()
        location = request.form.get('location', '').strip()
        rating = int(request.form.get('rating', 5))
        sort_order = int(request.form.get('sort_order', 0))
        testimonial = Testimonial(text=text, author=author, location=location, rating=rating, sort_order=sort_order)
        db.session.add(testimonial)
        db.session.commit()
        flash(f'Testimonial from {author} added.', 'success')
        return redirect(url_for('admin_testimonials'))
    return render_template('testimonial_edit.html', testimonial=None)

@app.route('/admin/testimonials/<int:testimonial_id>/edit/', methods=['GET', 'POST'])
@login_required
def admin_edit_testimonial(testimonial_id):
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    if request.method == 'POST':
        testimonial.text = request.form.get('text', '').strip()
        testimonial.author = request.form.get('author', '').strip()
        testimonial.location = request.form.get('location', '').strip()
        testimonial.rating = int(request.form.get('rating', 5))
        testimonial.sort_order = int(request.form.get('sort_order', 0))
        testimonial.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash('Testimonial updated.', 'success')
        return redirect(url_for('admin_testimonials'))
    return render_template('testimonial_edit.html', testimonial=testimonial)

@app.route('/admin/testimonials/<int:testimonial_id>/delete/', methods=['POST'])
@login_required
def admin_delete_testimonial(testimonial_id):
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    db.session.delete(testimonial)
    db.session.commit()
    flash('Testimonial deleted.', 'success')
    return redirect(url_for('admin_testimonials'))

# ===== Content Management: Rooms =====
@app.route('/admin/rooms/')
@login_required
def admin_rooms():
    rooms = Room.query.order_by(Room.sort_order, Room.created_at).all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/admin/rooms/create/', methods=['GET', 'POST'])
@login_required
def admin_create_room():
    if request.method == 'POST':
        room = Room(
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', ''),
            price=request.form.get('price', ''),
            image=request.form.get('image', ''),
            features=request.form.get('features', ''),
            sort_order=int(request.form.get('sort_order', 0))
        )
        db.session.add(room)
        db.session.commit()
        flash(f'Room "{room.name}" added.', 'success')
        return redirect(url_for('admin_rooms'))
    return render_template('room_edit.html', room=None)

@app.route('/admin/rooms/<int:room_id>/edit/', methods=['GET', 'POST'])
@login_required
def admin_edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.name = request.form.get('name', '').strip()
        room.description = request.form.get('description', '')
        room.price = request.form.get('price', '')
        room.image = request.form.get('image', '')
        room.features = request.form.get('features', '')
        room.sort_order = int(request.form.get('sort_order', 0))
        room.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Room "{room.name}" updated.', 'success')
        return redirect(url_for('admin_rooms'))
    return render_template('room_edit.html', room=room)

@app.route('/admin/rooms/<int:room_id>/delete/', methods=['POST'])
@login_required
def admin_delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted.', 'success')
    return redirect(url_for('admin_rooms'))

# ===== Content Management: Pages =====
@app.route('/admin/pages/')
@login_required
def admin_pages():
    return render_template('pages.html')

@app.route('/admin/pages/<page>/', methods=['GET', 'POST'])
@login_required
def admin_edit_page(page):
    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('content_'):
                section_key = key.replace('content_', '')
                section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                if section:
                    section.content = value.strip()
            elif key.startswith('title_'):
                section_key = key.replace('title_', '')
                section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                if section:
                    section.title = value.strip()
            elif key.startswith('meta_title_'):
                section_key = key.replace('meta_title_', '')
                section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                if section:
                    section.meta_title = value.strip()
            elif key.startswith('meta_description_'):
                section_key = key.replace('meta_description_', '')
                section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                if section:
                    section.meta_description = value.strip()
            elif key.startswith('existing_image_'):
                section_key = key.replace('existing_image_', '')
                section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                if section:
                    section.image = value.strip()

        for key, file in request.files.items():
            if key.startswith('image_'):
                section_key = key.replace('image_', '')
                if file and file.filename:
                    allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
                    ext = file.filename.rsplit('.', 1)[-1].lower()
                    if ext in allowed:
                        url = upload_to_cloudinary(file, 'latitude_zero/pages')
                        if url:
                            section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                            if section:
                                section.image = url

        db.session.commit()
        flash(f'{page.title()} page updated.', 'success')
        return redirect(url_for('admin_edit_page', page=page))
    sections = PageSection.get_for_page(page)
    return render_template('page_edit.html', page_name=page, sections=sections)

# ===== Gallery Admin =====
@app.route('/admin/gallery/')
@login_required
def admin_gallery():
    images = GalleryImage.get_active()
    return render_template('gallery_admin.html', images=images)

@app.route('/admin/gallery/add/', methods=['POST'])
@login_required
def admin_add_gallery_image():
    if 'image' not in request.files:
        flash('No image provided.', 'error')
        return redirect(url_for('admin_gallery'))
    file = request.files['image']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin_gallery'))
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        flash('File type not allowed. Use JPG, PNG, GIF, or WebP.', 'error')
        return redirect(url_for('admin_gallery'))
    try:
        url = upload_to_cloudinary(file, 'latitude_zero/gallery')
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('admin_gallery'))
    caption = request.form.get('caption', '')
    sort_order = int(request.form.get('sort_order', 0))
    new_image = GalleryImage(image=url, caption=caption, sort_order=sort_order)
    db.session.add(new_image)
    db.session.commit()
    flash('Image added to gallery.', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/admin/gallery/<int:image_id>/delete/', methods=['POST'])
@login_required
def admin_delete_gallery_image(image_id):
    image = GalleryImage.query.get_or_404(image_id)
    db.session.delete(image)
    db.session.commit()
    flash('Image deleted.', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/api/gallery/')
def api_gallery():
    images = GalleryImage.get_active()
    return jsonify({'images': [{'id': img.id, 'image': img.image, 'caption': img.caption, 'sort_order': img.sort_order} for img in images]})

# ===== Stats API ===
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

# ===== Pretty-URL redirects (parity with netlify.toml, which only applies on Netlify) =====
@app.route('/about')
@app.route('/services')
@app.route('/gallery')
@app.route('/contact')
def _pretty_page_redirect():
    page = request.path.strip('/')
    return redirect(f'/pages/{page}.html', code=301)


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

# Only these extensions may be served from the project root. This is a strict
# allowlist so the catch-all can NEVER hand out app.py, models.py, .env,
# requirements.txt, the SQLite db, or any other source/secret file.
ALLOWED_STATIC_EXT = {
    'html', 'htm', 'css', 'js', 'mjs', 'json', 'txt', 'xml', 'webmanifest',
    'ico', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'avif',
    'woff', 'woff2', 'ttf', 'eot', 'map',
}
# Project files that share an allowed extension (.txt) but must never be served.
BLOCKED_STATIC_BASENAMES = {'requirements.txt', 'runtime.txt'}


@app.route('/<path:filename>')
def serve_static(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    basename = filename.rsplit('/', 1)[-1].lower()
    if ext not in ALLOWED_STATIC_EXT or basename in BLOCKED_STATIC_BASENAMES:
        abort(404)
    return send_from_directory(BASE_DIR, filename)

# ===== Initialize Database =====
def _wait_for_db(max_wait=45, interval=1.5):
    """Wait for the database to accept connections before init runs.

    On a managed host the web service can start a moment before the Postgres
    container is ready ('the database system is starting up'). Rather than crash
    the boot, ping the DB and retry with backoff until it answers or we time out.
    On SQLite this succeeds on the first try, so local dev is unaffected.
    """
    deadline = time.time() + max_wait
    attempt = 0
    while True:
        attempt += 1
        try:
            db.session.execute(text('SELECT 1'))
            db.session.rollback()
            return
        except OperationalError as exc:
            db.session.rollback()
            if time.time() >= deadline:
                print(f'Database still unreachable after {max_wait}s — giving up.', file=sys.stderr)
                raise
            first_line = str(exc).splitlines()[0][:110]
            print(f'Database not ready (attempt {attempt}): {first_line} — retrying in {interval}s...', file=sys.stderr)
            time.sleep(interval)


def init_db():
    with app.app_context():
        _wait_for_db()
        try:
            db.create_all()
        except (OperationalError, ProgrammingError):
            # Belt-and-suspenders: if several workers boot without --preload and
            # race to create tables, the loser just backs off — tables now exist.
            db.session.rollback()
        if not User.query.filter_by(username='admin').first():
            admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
            admin_pass = os.environ.get('ADMIN_PASSWORD')
            if not admin_pass:
                raise RuntimeError('ADMIN_PASSWORD environment variable is not set. Aborting.')
            superuser = User(username=admin_user, email='admin@latitudezero.ug', is_superuser=True)
            superuser.set_password(admin_pass)
            db.session.add(superuser)

        if not SiteSettings.query.first():
            settings = SiteSettings(
                hero_title='Your Peaceful Stay Near Queen Elizabeth National Park',
                hero_subtitle='Welcome to Latitude Zero Cottages Kikorongo — a comfortable, relaxing getaway surrounded by the natural beauty of Kikorongo. Whether you are here for a safari, a romantic escape, or a quiet retreat, we offer warm hospitality, delicious meals, and a place to truly unwind.',
                hero_tagline='Comfortable Cottages. Delicious Meals. Natural Surroundings. Warm Hospitality.',
                whatsapp='+256 700 629 083',
                phone='+256 700 629 083',
                email='info@latitudezero.ug',
                address='Kikorongo, near Queen Elizabeth National Park'
            )
            db.session.add(settings)

        if not Testimonial.query.first():
            testimonials = [
                Testimonial(text='Absolutely wonderful stay! The staff were incredibly welcoming and the cottages are beautifully maintained. Woke up to birds singing and fell asleep to the sounds of nature. Will definitely come back!', author='Sarah M.', location='London, UK', rating=5, sort_order=1),
                Testimonial(text='Best lodge experience in Uganda. Clean, comfortable, and the food was excellent. Very close to Queen Elizabeth National Park — perfect for our safari adventures.', author='James K.', location='Nairobi, Kenya', rating=5, sort_order=2),
                Testimonial(text='A peaceful retreat with amazing hospitality. The team went above and beyond to make our anniversary special. Highly recommended for couples!', author='Anna & Peter', location='Amsterdam, NL', rating=5, sort_order=3),
            ]
            for t in testimonials:
                db.session.add(t)

        if not Room.query.first():
            rooms = [
                Room(name='Standard Room', description='A comfortable room with quality bedding and all essential amenities for a restful stay — perfect after a day in the park. One standard rate, everything included.', price='$150/night', image='/images/IMG_3396.jpeg', features='WiFi\nHot Shower\nComfortable Bedroom\nMosquito Net\nAC Available', sort_order=1),
            ]
            for r in rooms:
                db.session.add(r)

        if not PageSection.query.first():
            sections = [
                PageSection(page='about', section_key='hero', title='About Us', content='Latitude Zero Cottages Kikorongo is a peaceful accommodation destination located in Kikorongo, near the breathtaking landscapes of Queen Elizabeth National Park. We offer comfortable cottages, spacious rooms, delicious meals, refreshing drinks, beautiful natural surroundings, reliable 24/7 internet connection, and warm personalized hospitality.'),
                PageSection(page='about', section_key='mission', title='Our Mission', content='Our goal is to give every guest a comfortable and memorable stay, whether they are visiting for adventure, relaxation, family time, or a peaceful retreat.'),
                PageSection(page='about', section_key='story', title='Our Story', content='Established with a vision to offer visitors a serene home away from home near Queen Elizabeth National Park, Latitude Zero Cottages has grown into a beloved destination for nature enthusiasts, families, couples, and groups seeking authentic Ugandan hospitality.'),
                PageSection(page='services', section_key='hero', title='Our Services', content='At Latitude Zero Cottages Kikorongo, we offer more than just a place to stay. Our goal is to provide a comprehensive experience that blends comfort, relaxation, and adventure in one of Uganda most beautiful regions.'),
                PageSection(page='services', section_key='rooms', title='Comfortable Accommodation', content='Our comfortable Standard Rooms are designed for relaxation after a day of adventure. Each room offers modern amenities, quality bedding, an en-suite bathroom, and a peaceful atmosphere — one standard rate at $150/night, everything included.'),
                PageSection(page='services', section_key='dining', title='Delicious Dining', content='Enjoy freshly prepared local and international meals at our dining area. Our menu features a blend of traditional Ugandan dishes and continental favorites, all prepared with fresh ingredients.'),
                PageSection(page='services', section_key='safari', title='Safari Adventures', content='Just 300m from the Equator and beside Queen Elizabeth National Park, we offer easy access to wildlife safaris, game drives, boat cruises, and nature walks. Our team can help you plan the perfect safari adventure.'),
                PageSection(page='services', section_key='amenities', title='Amenities', content='All rooms include: 24/7 WiFi, hot showers, comfortable bedding, mosquito nets, power backup, and room service. Our facilities are designed to ensure a relaxing and worry-free stay.'),
                PageSection(page='gallery', section_key='hero', title='Gallery', content='Explore the beauty of Latitude Zero Cottages through our photo gallery. From the cottages and rooms to the stunning natural surroundings, see what awaits you.'),
                PageSection(page='contact', section_key='hero', title='Contact Us', content='Ready to book your stay? Have a question? We are here to help. Reach out to us via phone, WhatsApp, or email, and we will get back to you within 24 hours.'),
                PageSection(page='contact', section_key='intro', title='Book Your Stay', content='Fill out the form below and we will get back to you with availability and pricing. You can also reach out directly via WhatsApp for quick responses.'),
            ]
            for s in sections:
                db.session.add(s)

        if not GalleryImage.query.first():
            gallery = [
                ('/images/property-view.jpg', 'Our grounds & savanna views', 10),
                ('/images/guest-rooms.jpg', 'Guest rooms with private entrances', 20),
                ('/images/IMG_3396.jpeg', 'Comfortable room interiors', 30),
                ('/images/IMG_3389.jpeg', 'Modern en-suite bathrooms', 40),
                ('/images/IMG_3382.jpeg', 'Cottage exterior', 50),
                ('/images/IMG_3386.jpeg', 'Thatched cottages', 60),
                ('/images/IMG_3387.jpeg', 'Private verandas', 70),
                ('/images/IMG_3391.jpeg', 'Handcrafted timber ceilings', 80),
                ('/images/IMG_3395.jpeg', 'Savanna views', 90),
                ('/images/IMG_3393.jpeg', 'Green surroundings', 100),
                ('/images/IMG_3399.jpeg', 'Peaceful grounds', 110),
                ('/images/IMG_3385.jpeg', 'The road & the plains', 120),
            ]
            for src, caption, order in gallery:
                db.session.add(GalleryImage(image=src, caption=caption, sort_order=order))

        try:
            db.session.commit()
            print('Database initialized with seed content.')
        except (IntegrityError, OperationalError, ProgrammingError):
            # Under gunicorn -w N, several workers may seed concurrently on the
            # very first boot. Whoever loses the race just rolls back; the data
            # is already there.
            db.session.rollback()
            app.logger.warning('init_db seed skipped (already initialized by another worker).')


def apply_content_fixes():
    """One-off, idempotent corrections to seeded content.

    Each change fires ONLY when the stored value still exactly matches the old
    seeded default, so an admin's own edits are never overwritten. Safe to run on
    every boot — once corrected (or once an admin edits the field), it's a no-op.
    """
    fixes = {
        'hero_title': (
            'Your Peaceful Stay Near Queen Elizabeth National Park',
            'Wake Up to the Wild — 300m from the Equator',
        ),
        'hero_tagline': (
            'Comfortable Cottages. Delicious Meals. Natural Surroundings. Warm Hospitality.',
            '300m from the Equator · Beside Queen Elizabeth NP · Fresh Meals · 24/7 Wi-Fi',
        ),
    }
    with app.app_context():
        try:
            changed = False
            settings = SiteSettings.query.first()
            if settings:
                for field, (old, new) in fixes.items():
                    if getattr(settings, field, None) == old:
                        setattr(settings, field, new)
                        changed = True

            safari = PageSection.query.filter_by(page='services', section_key='safari').first()
            if safari and safari.content and 'Located just 1km from Queen Elizabeth National Park,' in safari.content:
                safari.content = safari.content.replace(
                    'Located just 1km from Queen Elizabeth National Park,',
                    'Just 300m from the Equator and beside Queen Elizabeth National Park,',
                )
                changed = True

            # Accommodation: one Standard room at $150, no variations. Each step
            # fires only while the value still matches the old seed, so admin edits
            # to rooms/pricing are never clobbered.
            std = Room.query.filter_by(name='Standard Room').first()
            if std and std.price == 'From $45/night':
                std.price = '$150/night'
                changed = True
            if std and std.image == 'images/IMG_3384.jpeg':
                std.image = 'images/IMG_3396.jpeg'  # actual room-interior photo (was a building exterior)
                changed = True

            # Make stored image paths absolute so they resolve on subpages too — a
            # relative 'images/x' on /pages/gallery.html becomes /pages/images/x (404).
            for gi in GalleryImage.query.all():
                if gi.image and gi.image.startswith('images/'):
                    gi.image = '/' + gi.image
                    changed = True
            if std and std.image and std.image.startswith('images/'):
                std.image = '/' + std.image
                changed = True

            rooms_sec = PageSection.query.filter_by(page='services', section_key='rooms').first()
            if rooms_sec and rooms_sec.content and 'a deluxe suite, or a family cottage' in rooms_sec.content:
                rooms_sec.content = ('Our comfortable Standard Rooms are designed for relaxation after a day of '
                                     'adventure. Each room offers modern amenities, quality bedding, an en-suite '
                                     'bathroom, and a peaceful atmosphere — one standard rate at $150/night, '
                                     'everything included.')
                changed = True
            for room_name, seed_price in (('Deluxe Room', 'From $65/night'), ('Family Cottage', 'From $85/night')):
                extra = Room.query.filter_by(name=room_name).first()
                if extra and extra.is_active and extra.price == seed_price:
                    extra.is_active = False  # hide (reversible) rather than delete
                    changed = True

            if changed:
                db.session.commit()
                print('Applied one-off content fixes (Equator distance).')
        except (IntegrityError, OperationalError, ProgrammingError):
            db.session.rollback()


init_db()
apply_content_fixes()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=_env_bool('FLASK_DEBUG', False))