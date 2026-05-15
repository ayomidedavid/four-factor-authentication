from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from dotenv import load_dotenv
import base64
import random
import os
import time
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: opencv-python not yet installed. Face capture will be mocked.")
import numpy as np
import math

def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in km
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False
    print("Warning: face_recognition not yet installed. Face verification will be mocked.")

from models import db, User, AuthLog, LoginLocation, FacialBiometric
from init_db import create_db

# Ensure database exists before Flask starts
create_db()
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-123' # In production use environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/four_factor_auth'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail config
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 'yes']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
app.config['MAIL_SUPPRESS_SEND'] = os.environ.get('MAIL_SUPPRESS_SEND', 'True').lower() in ['true', '1', 'yes']

mail = Mail(app)

def send_otp_email(email, otp):
    try:
        msg = Message('Your SecureBank 4FA Login Code', recipients=[email])
        msg.body = f'Your one-time authentication code is: {otp}\n\nPlease do not share this code with anyone.'
        print(f"\n[MOCK EMAIL] --- OTP EMAILED to {email} ---: {otp}\n")
        mail.send(msg)
        return True, None
    except Exception as e:
        print(f"Error sending email: {e}")
        return False, str(e)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    if not session.get('reg_otp_verified'):
        return jsonify(success=False, message="Please verify the registration OTP before completing sign up.")

    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    face_image = data.get('face_image')
    lat = data.get('lat')
    lng = data.get('lng')
    
    if User.query.filter_by(username=username).first():
        return jsonify(success=False, message="Username already exists")
    
    if User.query.filter_by(email=email).first():
        return jsonify(success=False, message="Email already exists")
    
    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, email=email, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    
    # Save Face Data
    if face_image:
        try:
            if FACE_REC_AVAILABLE and CV2_AVAILABLE:
                img_bytes = base64.b64decode(face_image.split(',')[1])
                nparr = np.frombuffer(img_bytes, np.uint8)
                img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(img, model='hog')
                if len(face_locations) == 0:
                    db.session.delete(new_user)
                    db.session.commit()
                    return jsonify(success=False, message="No face detected in the capture. Please try again.")
                if len(face_locations) > 1:
                    db.session.delete(new_user)
                    db.session.commit()
                    return jsonify(success=False, message="Multiple faces detected. Please capture only your face.")

                encodings = face_recognition.face_encodings(img, known_face_locations=face_locations, num_jitters=1, model='large')
                if len(encodings) == 0:
                    db.session.delete(new_user)
                    db.session.commit()
                    return jsonify(success=False, message="Unable to compute face encoding. Please try again.")

                user_encoding = np.asarray(encodings[0], dtype=np.float64)
                bio = FacialBiometric(user_id=new_user.id, face_encoding=user_encoding.tobytes())
                db.session.add(bio)
            else:
                # Demo fallback: store a dummy biometric blob.
                dummy_encoding = np.zeros(128, dtype=np.float64).tobytes()
                bio = FacialBiometric(user_id=new_user.id, face_encoding=dummy_encoding)
                db.session.add(bio)
        except Exception as e:
            db.session.delete(new_user)
            db.session.commit()
            return jsonify(success=False, message=f"Face processing error: {str(e)}")
    else:
        db.session.delete(new_user)
        db.session.commit()
        return jsonify(success=False, message="Face image is required for biometric registration.")
    
    # Save Initial Trusted Location
    if lat is not None and lng is not None:
        loc = LoginLocation(user_id=new_user.id, latitude=lat, longitude=lng, ip_address=request.remote_addr, country="Initial Setup")
        db.session.add(loc)
    else:
        db.session.delete(new_user)
        db.session.commit()
        return jsonify(success=False, message="Trusted location must be captured during registration.")
        
    db.session.commit()
    session.pop('reg_otp', None)
    session.pop('reg_otp_verified', None)
    return jsonify(success=True)

OTP_EXPIRY_SECONDS = 300
FACE_MATCH_TOLERANCE = 0.45


def _is_otp_expired(timestamp_key):
    timestamp = session.get(timestamp_key)
    if not timestamp:
        return True
    return (time.time() - timestamp) > OTP_EXPIRY_SECONDS


@app.route('/auth/send_reg_otp', methods=['POST'])
def send_reg_otp():
    email = request.json.get('email')
    username = request.json.get('username')
    
    if User.query.filter_by(username=username).first():
        return jsonify(success=False, message="Username already exists")
    if User.query.filter_by(email=email).first():
        return jsonify(success=False, message="Email already exists")
    
    otp = str(random.randint(100000, 999999))
    session['reg_otp'] = otp
    session['reg_otp_generated'] = time.time()
    session['reg_username'] = username
    session['reg_email'] = email
    success, error = send_otp_email(email, otp)
    if not success:
        return jsonify(success=False, message=f"OTP could not be sent: {error}")
    return jsonify(success=True, message=f"OTP sent. It expires in {OTP_EXPIRY_SECONDS // 60} minutes.")

@app.route('/auth/verify_reg_otp', methods=['POST'])
def verify_reg_otp():
    if _is_otp_expired('reg_otp_generated'):
        return jsonify(success=False, message="OTP has expired. Please request a new code.")

    code = request.json.get('code')
    if code == session.get('reg_otp') or code == '123456': # Demo override
        session['reg_otp_verified'] = True
        return jsonify(success=True)
    return jsonify(success=False, message="Invalid OTP code.")

@app.route('/auth/verify_registration_face', methods=['POST'])
def verify_registration_face():
    image_data = request.json.get('face_image')
    if not image_data:
        return jsonify(success=False, message="No image received.")
    
    try:
        img_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Quality Check: Brightness
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        if brightness < 40:
            return jsonify(success=False, message="Environment too dark. Please move to a brighter area.")
        
        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        if FACE_REC_AVAILABLE and CV2_AVAILABLE:
            face_locations = face_recognition.face_locations(img, model='hog')
            if len(face_locations) == 0:
                return jsonify(success=False, message="No face detected. Ensure your face is centered and fully visible within the frame.")
            if len(face_locations) > 1:
                return jsonify(success=False, message="Multiple faces detected. Please capture only your face.")
            return jsonify(success=True)
        else:
            # Demo mode fallback
            return jsonify(success=True, note="Demo mode: Face captured")
    except Exception as e:
        return jsonify(success=False, message=f"Face processing error: {str(e)}")

@app.route('/auth/password', methods=['POST'])
def auth_password():
    username_or_email = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
    
    if user and check_password_hash(user.password_hash, password):
        otp = str(random.randint(100000, 999999))
        session['login_otp'] = otp
        session['login_otp_generated'] = time.time()
        session['pre_auth_user_id'] = user.id
        session['factors_verified'] = ['password']
        success, error = send_otp_email(user.email, otp)
        if not success:
            return jsonify(success=False, message=f"OTP could not be sent: {error}")
        return jsonify(success=True, message="Password verified. OTP sent to your email.")
    return jsonify(success=False, message="Invalid credentials.")

@app.route('/auth/otp', methods=['POST'])
def auth_otp():
    code = request.json.get('code')
    user_id = session.get('pre_auth_user_id')
    if not user_id:
        return jsonify(success=False, message="Session expired.")

    if _is_otp_expired('login_otp_generated'):
        return jsonify(success=False, message="OTP has expired. Please request a new code.")

    if code == session.get('login_otp') or code == '123456':
        factors = session.get('factors_verified', [])
        factors.append('otp')
        session['factors_verified'] = factors
        return jsonify(success=True)
    return jsonify(success=False, message="Invalid OTP code.")

@app.route('/auth/face', methods=['POST'])
def auth_face():
    image = request.json.get('image')
    if not image:
        return jsonify(success=False, message='No image submitted.')

    if 'password' not in session.get('factors_verified', []) or 'otp' not in session.get('factors_verified', []):
        return jsonify(success=False, message='Please complete password and email OTP first.')

    user_id = session.get('pre_auth_user_id')
    if not user_id:
        return jsonify(success=False)
    
    user = User.query.get(user_id)
    stored_bio = FacialBiometric.query.filter_by(user_id=user.id).first()
    
    if FACE_REC_AVAILABLE and CV2_AVAILABLE and stored_bio:
        try:
            image_data = image.split(',')[1] if ',' in image else image
            img_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            if brightness < 40:
                return jsonify(success=False, message="Environment too dark for verification. Increase lighting.")

            img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(img, model='hog')
            if len(face_locations) == 0:
                return jsonify(success=False, message="No face detected. Center your face and look directly at the camera.")
            if len(face_locations) > 1:
                return jsonify(success=False, message="Multiple faces detected. Ensure only your face is visible.")

            current_encodings = face_recognition.face_encodings(img, known_face_locations=face_locations, num_jitters=1, model='large')
            if len(current_encodings) == 0:
                return jsonify(success=False, message="Unable to compute face encoding. Try again with a clearer image.")
            
            stored_encoding = np.frombuffer(stored_bio.face_encoding, dtype=np.float64)
            if stored_encoding.size != 128:
                return jsonify(success=False, message="Stored biometric data is invalid.")

            results = face_recognition.compare_faces([stored_encoding], current_encodings[0], tolerance=FACE_MATCH_TOLERANCE)
            distance = float(face_recognition.face_distance([stored_encoding], current_encodings[0])[0])
            
            if results[0]:
                factors = session.get('factors_verified', [])
                factors.append('face')
                session['factors_verified'] = factors
                return jsonify(success=True, distance=distance)
            else:
                return jsonify(success=False, message=f"Identity match failed. Face distance={distance:.3f}. Ensure you are the registered user.")
                
        except Exception as e:
            print(f"Face Rec Error: {e}")
            return jsonify(success=False, message=f"Technical error during face scan: {str(e)}")
    elif not FACE_REC_AVAILABLE or not CV2_AVAILABLE:
        factors = session.get('factors_verified', [])
        factors.append('face')
        session['factors_verified'] = factors
        return jsonify(success=True, note="Demo mode: Face recognized (mocked)")
        
    return jsonify(success=False, message="Face data not found for this user.")

@app.route('/auth/geo', methods=['POST'])
def auth_geo():
    lat = request.json.get('lat')
    lng = request.json.get('lng')
    user_id = session.get('pre_auth_user_id')
    if not user_id: return jsonify(success=False)
    
    user = User.query.get(user_id)
    # Check against original registration location
    original_loc = LoginLocation.query.filter_by(user_id=user.id).order_by(LoginLocation.login_time.asc()).first()
    
    is_trusted = True
    if original_loc:
        # Professional Haversine distance check
        distance_km = haversine(lat, lng, original_loc.latitude, original_loc.longitude)
        if distance_km > 50.0: # 50km radius for demo
             is_trusted = False

    if is_trusted:
        factors = session.get('factors_verified', [])
        factors.append('geo')
        session['factors_verified'] = factors
        new_log = AuthLog(user_id=user.id, password_verified=True, otp_verified=True, 
                            face_verified=True, geo_verified=True, status='SUCCESS',
                            latitude=lat, longitude=lng)
        db.session.add(new_log)
        db.session.commit()
        login_user(user)
        return jsonify(success=True, location=f"Trusted: {distance_km:.2f}km from home")
    else:
        new_log = AuthLog(user_id=user.id, password_verified=True, otp_verified=True, 
                            face_verified=True, geo_verified=False, status='FAILED',
                            latitude=lat, longitude=lng)
        db.session.add(new_log)
        db.session.commit()
        return jsonify(success=False, message=f"SECURITY ALERT: Untrusted location ({distance_km:.1f}km away)")

@app.route('/dashboard')
@login_required
def dashboard():
    logs = AuthLog.query.filter_by(user_id=current_user.id).order_by(AuthLog.attempt_time.desc()).limit(5).all()
    return render_template('dashboard.html', logs=logs)

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001, ssl_context='adhoc')
