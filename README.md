# SecureBank 4-Factor Authentication

This repository implements a four-factor authentication system using Flask.
It is designed to collect and verify the following factors:

1. Username + Email + Password
2. Email OTP verification
3. Face biometric verification
4. Geolocation verification

## Flow Summary

### Registration
1. User enters username, email, and password.
2. System sends a one-time email OTP.
3. User verifies the OTP.
4. User captures face data through guided face pose instructions.
5. Application records the user's current location as trusted baseline.
6. Registration completes and the user may proceed to login.

### Login
1. User enters username and password.
2. System sends an email OTP to the registered address.
3. User verifies the OTP.
4. User completes a face recognition step.
5. System verifies the current geolocation against the registered baseline.
6. If all checks pass, user is redirected to the dashboard.

## Key Files

- `app.py` - Flask backend with registration, OTP, face verification, and geo logic.
- `models.py` - SQLAlchemy models for users, biometrics, locations, and authentication logs.
- `templates/login.html` - Front-end multi-step authentication experience.
- `static/js/main.js` - Client-side flow control for OTP, face capture, and geolocation.
- `requirements.txt` - Python dependencies.

## Setup

1. Create and activate a Python virtual environment.

```powershell
python -m venv venv
.& venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Configure email settings.

### Option A: Environment variables (recommended)
Set the following before running the app:

```powershell
$env:MAIL_SERVER = 'smtp.gmail.com'
$env:MAIL_PORT = '587'
$env:MAIL_USE_TLS = 'True'
$env:MAIL_USERNAME = 'your_email@gmail.com'
$env:MAIL_PASSWORD = 'your_app_password'
$env:MAIL_DEFAULT_SENDER = 'your_email@gmail.com'
$env:MAIL_SUPPRESS_SEND = 'False'
```

### Option B: Hardcode values in `app.py`
Update the `MAIL_*` values in `app.py` if you prefer not to use environment variables.

4. Ensure your MySQL database is available and connection details in `app.py` are correct.

5. Run the app.

```powershell
python app.py
```

6. Open the browser at `https://localhost:5001`.

## Notes

- `flask-mail` is currently configured to mock email sending using console output.
- Face recognition requires `opencv-python` and `face_recognition` to be installed.
- Geolocation is captured via the browser's `navigator.geolocation` API.
- OTP codes expire after 5 minutes by default.
- For real-world production use, update the secret key and mail credentials to use secure environment variables.

## Improvements

Possible next enhancements:

- Store the OTP expiration time to reject stale codes.
- Add HTTPS certificate management for production.
- Add better error handling for browser permission denial.
- Use a dedicated face model or API for improved biometric accuracy.

## Password Visibility

Both login and registration forms include a password visibility toggle (an eye icon) so users can reveal/hide the password while typing. The toggle state is reflected visually and is keyboard accessible.

## Theme Toggle

A global theme toggle is available in the top-right of the UI. The app supports a dark default theme and a light theme; the user's choice is persisted in `localStorage`.

## Clearing the Database

A helper script is included to clear all data and recreate the schema:

```powershell
python clear_db.py
```

This will drop all tables and recreate them with the current model definitions.

## Face Capture Preview Videos

The face recognition steps now include preview videos showing expected head movements. To enable:

1. Create short MP4 videos or GIFs for each pose:
   - `static/videos/center.mp4` - Face looking straight ahead
   - `static/videos/left.mp4` - Head turning left
   - `static/videos/right.mp4` - Head turning right
   - `static/videos/up.mp4` - Head tilting up
   - `static/videos/down.mp4` - Head tilting down

2. Videos should be ~100x100px, looping animations.

If videos are missing, the preview area will be empty but instructions still work.
