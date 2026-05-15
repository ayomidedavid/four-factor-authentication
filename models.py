from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    locations = db.relationship('LoginLocation', backref='user', lazy=True)
    devices = db.relationship('TrustedDevice', backref='user', lazy=True)
    biometrics = db.relationship('FacialBiometric', backref='user', uselist=False)
    logs = db.relationship('AuthLog', backref='user', lazy=True)

class LoginLocation(db.Model):
    __tablename__ = 'login_locations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)

class TrustedDevice(db.Model):
    __tablename__ = 'trusted_devices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_name = db.Column(db.String(100))
    device_fingerprint = db.Column(db.String(255), unique=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class FacialBiometric(db.Model):
    __tablename__ = 'facial_data'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    face_encoding = db.Column(db.LargeBinary, nullable=False) # Store encodings as binary
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuthLog(db.Model):
    __tablename__ = 'authentication_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    password_verified = db.Column(db.Boolean, default=False)
    otp_verified = db.Column('totp_verified', db.Boolean, default=False)
    face_verified = db.Column(db.Boolean, default=False)
    geo_verified = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20)) # SUCCESS, FAILED
    attempt_time = db.Column(db.DateTime, default=datetime.utcnow)
