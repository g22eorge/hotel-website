from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    checkin = db.Column(db.Date, nullable=False)
    checkout = db.Column(db.Date, nullable=False)
    guests = db.Column(db.String(20), nullable=False)
    room = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40))
    requests = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    source = db.Column(db.String(20), default='whatsapp')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Booking {self.id}: {self.name}>'

    @property
    def nights(self):
        if self.checkout and self.checkin:
            return (self.checkout - self.checkin).days
        return 0

class SiteSettings(db.Model):
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True)
    hero_title = db.Column(db.String(200), default='Your Peaceful Stay Near Queen Elizabeth National Park')
    hero_subtitle = db.Column(db.Text, default='')
    hero_tagline = db.Column(db.String(300), default='')
    whatsapp = db.Column(db.String(40), default='+256 700 629 083')
    phone = db.Column(db.String(40), default='+256 700 629 083')
    email = db.Column(db.String(120), default='info@latitudezero.ug')
    address = db.Column(db.String(200), default='Kikorongo, near Queen Elizabeth National Park')
    facebook = db.Column(db.String(200), default='')
    instagram = db.Column(db.String(200), default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings

class Testimonial(db.Model):
    __tablename__ = 'testimonials'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), default='')
    rating = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order, cls.created_at.desc()).all()

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    price = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), default='')
    features = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order, cls.created_at).all()

class PageSection(db.Model):
    __tablename__ = 'page_sections'

    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(50), nullable=False)
    section_key = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), default='')
    content = db.Column(db.Text, default='')
    image = db.Column(db.String(200), default='')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_for_page(cls, page):
        return cls.query.filter_by(page=page, is_active=True).order_by(cls.sort_order).all()

    @classmethod
    def get_by_key(cls, page, section_key):
        return cls.query.filter_by(page=page, section_key=section_key).first()

    @classmethod
    def upsert(cls, page, section_key, **kwargs):
        section = cls.query.filter_by(page=page, section_key=section_key).first()
        if not section:
            section = cls(page=page, section_key=section_key)
            db.session.add(section)
        for key, value in kwargs.items():
            if hasattr(section, key):
                setattr(section, key, value)
        db.session.commit()
        return section
