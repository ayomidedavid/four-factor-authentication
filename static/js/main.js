let currentStep = 'initial';
let registrationData = {};
const activeStreams = {};

function stopVideoStream(videoId) {
    const video = document.getElementById(videoId);
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    delete activeStreams[videoId];
}

function estimateBrightnessFromCanvas(canvas) {
    const ctx = canvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let valueSum = 0;
    for (let i = 0; i < imageData.length; i += 4) {
        const r = imageData[i];
        const g = imageData[i + 1];
        const b = imageData[i + 2];
        valueSum += 0.299 * r + 0.587 * g + 0.114 * b;
    }
    return valueSum / (imageData.length / 4);
}

function initWebcam(videoId, type) {
    const video = document.getElementById(videoId);
    const statusEl = document.getElementById(type === 'reg' ? 'reg-face-status' : 'login-face-status');
    const button = document.getElementById(type === 'reg' ? 'reg-face-btn' : 'login-face-btn');

    if (!video || !statusEl) return;
    if (button) button.disabled = true;
    statusEl.innerText = '⏳ Starting camera...';

    stopVideoStream(videoId);

    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(stream => {
            video.srcObject = stream;
            activeStreams[videoId] = stream;
            const handleReady = () => {
                if (video.videoWidth > 0 && video.videoHeight > 0) {
                    statusEl.innerText = '✓ Camera ready - align your face and click capture';
                    if (button) button.disabled = false;
                    video.removeEventListener('loadedmetadata', handleReady);
                }
            };
            video.addEventListener('loadedmetadata', handleReady);
            video.play().catch(() => {});

            setTimeout(() => {
                if (video.videoWidth > 0 && video.videoHeight > 0) {
                    statusEl.innerText = '✓ Camera ready - align your face and click capture';
                    if (button) button.disabled = false;
                } else {
                    statusEl.innerText = '❌ Camera not ready yet. Please retry.';
                    if (button) button.disabled = true;
                }
            }, 1500);
        })
        .catch(err => {
            console.error('Webcam error:', err);
            statusEl.innerText = '❌ Camera access denied';
            alert('Please allow webcam access to continue.');
            if (button) button.disabled = true;
        });
}

// --- Registration Flow ---

function regStep2() {
    const form = document.getElementById('register-form');
    const formData = new FormData(form);
    registrationData.username = formData.get('username');
    registrationData.email = formData.get('email');
    registrationData.password = formData.get('password');
}

async function sendRegistrationOTP() {
    const usernameInput = document.getElementById('reg-username');
    const emailInput = document.getElementById('reg-email');
    const passwordInput = document.getElementById('reg-password');

    registrationData.username = usernameInput ? usernameInput.value.trim() : registrationData.username;
    registrationData.email = emailInput ? emailInput.value.trim() : registrationData.email;
    registrationData.password = passwordInput ? passwordInput.value.trim() : registrationData.password;

    if (!registrationData.username || !registrationData.email || !registrationData.password) {
        alert('Please enter username, email, and password before sending the OTP.');
        return;
    }

    const button = document.querySelector('#step-register-1 button');
    if (button) {
        button.disabled = true;
        button.innerText = 'Sending...';
    }

    try {
        const response = await fetch('/auth/send_reg_otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: registrationData.username,
                email: registrationData.email
            })
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server returned ${response.status}: ${text}`);
        }

        const data = await response.json();
        if (data.success) {
            transitionTo('register-otp');
        } else {
            alert(data.message || 'Unable to send OTP.');
        }
    } catch (err) {
        console.error('sendRegistrationOTP error:', err);
        alert('Unable to send OTP. ' + (err.message || 'Please check the server and try again.'));
    } finally {
        if (button) {
            button.disabled = false;
            button.innerText = 'Send OTP';
        }
    }
}

async function resendRegistrationOTP() {
    const usernameInput = document.getElementById('reg-username');
    const emailInput = document.getElementById('reg-email');

    registrationData.username = usernameInput ? usernameInput.value.trim() : registrationData.username;
    registrationData.email = emailInput ? emailInput.value.trim() : registrationData.email;

    if (!registrationData.email || !registrationData.username) {
        alert('Please re-enter your registration details.');
        transitionTo('register-1');
        return;
    }
    await sendRegistrationOTP();
}

async function verifyRegistrationOTP() {
    const code = document.getElementById('reg-otp').value;
    try {
        const response = await fetch('/auth/verify_reg_otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server returned ${response.status}: ${text}`);
        }

        const data = await response.json();
        console.log('verifyRegistrationOTP response', data);
        if (data.success) {
            transitionTo('register-face');
        } else {
            alert(data.message || 'Invalid registration OTP.');
        }
    } catch (err) {
        console.error('verifyRegistrationOTP error:', err);
        alert('Unable to verify OTP. ' + (err.message || 'Please try again.'));
    }
}

// --- Simple Face Capture ---

async function captureFaceReg() {
    const video = document.getElementById('webcam-reg');
    const statusEl = document.getElementById('reg-face-status');
    const btn = document.getElementById('reg-face-btn');
    
    btn.disabled = true;
    statusEl.innerText = '📷 Capturing...';
    
    try {
        if (!video || !video.videoWidth || !video.videoHeight) {
            statusEl.innerText = '❌ Camera is not ready yet.';
            btn.disabled = false;
            return;
        }

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        const brightness = estimateBrightnessFromCanvas(canvas);
        if (brightness < 45) {
            statusEl.innerText = '❌ Too dark. Increase lighting and try again.';
            btn.disabled = false;
            return;
        }

        const imageData = canvas.toDataURL('image/jpeg');
        statusEl.innerText = '⏳ Processing...';
        
        const response = await fetch('/auth/verify_registration_face', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ face_image: imageData })
        });
        const data = await response.json();

        if (data.success) {
            registrationData.face_image = imageData;
            statusEl.innerText = '✓ Face captured successfully!';
            
            stopVideoStream('webcam-reg');
            
            setTimeout(() => {
                transitionTo('register-geo');
                detectRegGeo();
            }, 1000);
        } else {
            statusEl.innerText = '❌ ' + (data.message || 'Face capture failed');
            btn.disabled = false;
        }
    } catch (err) {
        console.error(err);
        statusEl.innerText = '❌ Error capturing face';
        btn.disabled = false;
    }
}

function detectRegGeo() {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition((position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            registrationData.lat = lat;
            registrationData.lng = lng;
            
            document.getElementById('reg-location-text').innerText = '✓ Location acquired';
            document.getElementById('reg-lat').innerText = lat.toFixed(6);
            document.getElementById('reg-lng').innerText = lng.toFixed(6);
            document.getElementById('reg-coords').style.display = 'flex';
            document.getElementById('reg-geo-btn').style.display = 'block';
        }, (err) => {
            alert("Location access denied. Using mock location for demo.");
            registrationData.lat = 6.5244;
            registrationData.lng = 3.3792;
            document.getElementById('reg-location-text').innerText = '📍 Location (Mock)';
            document.getElementById('reg-lat').innerText = "6.524400";
            document.getElementById('reg-lng').innerText = "3.379200";
            document.getElementById('reg-coords').style.display = 'flex';
            document.getElementById('reg-geo-btn').style.display = 'block';
        });
    }
}

async function handleFinalRegister() {
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(registrationData)
        });
        const data = await response.json();
        
        if (data.success) {
            alert('Registration complete! Redirecting to login.');
            window.location.href = '/login';
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error(err);
        alert('Registration failed. Please try again.');
    }
}

// --- Login Flow ---

async function proceedToFactor2() {
    const form = document.getElementById('login-form');
    const formData = new FormData(form);
    
    const response = await fetch('/auth/password', {
        method: 'POST',
        credentials: 'same-origin',
        body: formData
    });
    const data = await response.json();
    
    if (data.success) {
        alert(data.message || 'OTP sent to your email.');
        transitionTo('otp');
    } else {
        alert(data.message || 'Invalid credentials');
    }
}

async function proceedToFactor3() {
    const code = document.getElementById('otp-code').value;
    const response = await fetch('/auth/otp', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    });
    const data = await response.json();
    
    if (data.success) {
        transitionTo('face');
        initWebcam('webcam', 'login');
    } else {
        alert(data.message || 'Invalid OTP code');
    }
}

async function captureFaceLogin() {
    const video = document.getElementById('webcam');
    const statusEl = document.getElementById('login-face-status');
    const btn = document.getElementById('login-face-btn');
    
    btn.disabled = true;
    statusEl.innerText = '📷 Verifying...';
    
    try {
        if (!video || !video.videoWidth || !video.videoHeight) {
            statusEl.innerText = '❌ Camera is not ready yet.';
            btn.disabled = false;
            return;
        }

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        const brightness = estimateBrightnessFromCanvas(canvas);
        if (brightness < 45) {
            statusEl.innerText = '❌ Too dark. Increase lighting and try again.';
            btn.disabled = false;
            return;
        }

        const imageData = canvas.toDataURL('image/jpeg');
        statusEl.innerText = '⏳ Processing...';
        
        const response = await fetch('/auth/face', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const data = await response.json();

        if (data.success) {
            statusEl.innerText = '✓ Identity verified!';
            stopVideoStream('webcam');
            setTimeout(() => {
                transitionTo('geo');
                detectLoginGeo();
            }, 1500);
        } else {
            statusEl.innerText = '❌ ' + (data.message || 'Face not recognized');
            btn.disabled = false;
        }
    } catch (err) {
        console.error(err);
        statusEl.innerText = '❌ Error verifying face';
        btn.disabled = false;
    }
}

function detectLoginGeo() {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            const { latitude, longitude } = position.coords;
            
            document.getElementById('location-text').innerText = '✓ Location verified';
            document.getElementById('login-lat').innerText = latitude.toFixed(6);
            document.getElementById('login-lng').innerText = longitude.toFixed(6);
            document.getElementById('login-coords').style.display = 'flex';

            const response = await fetch('/auth/geo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: latitude, lng: longitude })
            });
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('finish-btn').style.display = 'block';
            } else {
                alert('Untrusted Location detected.');
                window.location.reload();
            }
        }, () => {
            alert("Location access denied");
        });
    }
}

function finalizeAuth() {
    window.location.href = '/dashboard';
}

function transitionTo(stepId) {
    document.querySelectorAll('.auth-step').forEach(step => step.classList.remove('active'));
    document.getElementById('step-' + stepId).classList.add('active');
    currentStep = stepId;

    if (stepId === 'register-face') {
        initWebcam('webcam-reg', 'reg');
    }
    if (stepId === 'face') {
        initWebcam('webcam', 'login');
    }
}

function togglePasswordVisibility(fieldId, checkbox) {
    const input = document.getElementById(fieldId);
    if (!input) return;
        const wasPassword = input.type === 'password';
        input.type = wasPassword ? 'text' : 'password';

        if (!checkbox) return;
        const tag = checkbox.tagName.toUpperCase();
        if (tag === 'INPUT' && checkbox.type === 'checkbox') {
            checkbox.checked = input.type === 'text';
        } else if (tag === 'BUTTON') {
            // update button icon and aria state
            checkbox.innerText = input.type === 'text' ? '🙈' : '👁️';
            checkbox.setAttribute('aria-pressed', input.type === 'text');
        }
}

function setTheme(theme) {
    const body = document.body;
    const buttons = document.querySelectorAll('#theme-toggle-btn, #theme-toggle-btn-auth');
    body.classList.toggle('light-mode', theme === 'light');
    buttons.forEach(button => {
        if (button) button.textContent = theme === 'light' ? 'Dark mode' : 'Light mode';
    });
    localStorage.setItem('theme', theme);
}

function toggleTheme() {
    const current = document.body.classList.contains('light-mode') ? 'light' : 'dark';
    setTheme(current === 'light' ? 'dark' : 'light');
}

window.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
});
