import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Booking, SiteSettings, Testimonial, Room, PageSection
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'latitude-zero-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'latitude_zero.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'images', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        },
        'contact': {
            'whatsapp': settings.whatsapp,
            'phone': settings.phone,
            'email': settings.email,
            'address': settings.address,
            'facebook': settings.facebook,
            'instagram': settings.instagram,
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
        return jsonify({'error': 'File type not allowed'}), 400
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return jsonify({'url': f'/images/uploads/{filename}'})

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
                        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        section = PageSection.query.filter_by(page=page, section_key=section_key).first()
                        if section:
                            section.image = f'/images/uploads/{filename}'

        db.session.commit()
        flash(f'{page.title()} page updated.', 'success')
        return redirect(url_for('admin_edit_page', page=page))
    sections = PageSection.get_for_page(page)
    return render_template('page_edit.html', page_name=page, sections=sections)

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
                Room(name='Standard Room', description='A cozy room with comfortable bedding and all essential amenities for a restful stay. Perfect for solo travelers or couples looking for comfort in nature.', price='From $45/night', image='images/IMG_3384.jpeg', features='WiFi\nHot Shower\nBedroom\nMosquito Net\nAC Available', sort_order=1),
                Room(name='Deluxe Room', description='Extra spacious room with premium furnishings and stunning views of the surrounding landscape. Ideal for those who want a little more space and luxury.', price='From $65/night', image='images/IMG_3385.jpeg', features='WiFi\nHot Shower\nSpacious Bedroom\nBalcony\nMosquito Net\nAC', sort_order=2),
                Room(name='Family Cottage', description='Ideal for families and groups, offering generous space and a private cottage setting with separate sleeping areas.', price='From $85/night', image='images/IMG_3388.jpeg', features='WiFi\nHot Shower\n2 Bedrooms\nLiving Area\nPrivate Cottage\nKitchenette', sort_order=3),
            ]
            for r in rooms:
                db.session.add(r)

        if not PageSection.query.first():
            sections = [
                PageSection(page='about', section_key='hero', title='About Us', content='Latitude Zero Cottages Kikorongo is a peaceful accommodation destination located in Kikorongo, near the breathtaking landscapes of Queen Elizabeth National Park. We offer comfortable cottages, spacious rooms, delicious meals, refreshing drinks, beautiful natural surroundings, reliable 24/7 internet connection, and warm personalized hospitality.'),
                PageSection(page='about', section_key='mission', title='Our Mission', content='Our goal is to give every guest a comfortable and memorable stay, whether they are visiting for adventure, relaxation, family time, or a peaceful retreat.'),
                PageSection(page='about', section_key='story', title='Our Story', content='Established with a vision to offer visitors a serene home away from home near Queen Elizabeth National Park, Latitude Zero Cottages has grown into a beloved destination for nature enthusiasts, families, couples, and groups seeking authentic Ugandan hospitality.'),
                PageSection(page='services', section_key='hero', title='Our Services', content='At Latitude Zero Cottages Kikorongo, we offer more than just a place to stay. Our goal is to provide a comprehensive experience that blends comfort, relaxation, and adventure in one of Uganda most beautiful regions.'),
                PageSection(page='services', section_key='rooms', title='Comfortable Accommodation', content='Our cottages and rooms are designed for relaxation after a day of adventure. Each room offers modern amenities, comfortable bedding, and a peaceful atmosphere. Whether you prefer a standard room, a deluxe suite, or a family cottage, we have the perfect space for your stay.'),
                PageSection(page='services', section_key='dining', title='Delicious Dining', content='Enjoy freshly prepared local and international meals at our dining area. Our menu features a blend of traditional Ugandan dishes and continental favorites, all prepared with fresh ingredients.'),
                PageSection(page='services', section_key='safari', title='Safari Adventures', content='Located just 1km from Queen Elizabeth National Park, we offer easy access to wildlife safaris, game drives, boat cruises, and nature walks. Our team can help you plan the perfect safari adventure.'),
                PageSection(page='services', section_key='amenities', title='Amenities', content='All rooms include: 24/7 WiFi, hot showers, comfortable bedding, mosquito nets, power backup, and room service. Our facilities are designed to ensure a relaxing and worry-free stay.'),
                PageSection(page='gallery', section_key='hero', title='Gallery', content='Explore the beauty of Latitude Zero Cottages through our photo gallery. From the cottages and rooms to the stunning natural surroundings, see what awaits you.'),
                PageSection(page='contact', section_key='hero', title='Contact Us', content='Ready to book your stay? Have a question? We are here to help. Reach out to us via phone, WhatsApp, or email, and we will get back to you within 24 hours.'),
                PageSection(page='contact', section_key='intro', title='Book Your Stay', content='Fill out the form below and we will get back to you with availability and pricing. You can also reach out directly via WhatsApp for quick responses.'),
            ]
            for s in sections:
                db.session.add(s)

        db.session.commit()
        print('Database initialized with seed content.')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)