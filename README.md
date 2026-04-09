🔐 Keystroke Logging Demonstration System
⚠️ EDUCATIONAL & ETHICAL USE ONLY This project is built strictly for cybersecurity awareness, academic learning, and ethical demonstration. Never use keystroke logging to monitor others without explicit consent. Doing so is illegal in most jurisdictions.

📁 Project Structure
Keystroke Logging Demonstration/
│
├── backend/                    ← Python FastAPI Server
│   ├── main.py                 ← FastAPI app + all REST & WebSocket endpoints
│   ├── logger.py               ← pynput-based keystroke capture engine
│   ├── storage.py              ← Fernet-encrypted file storage + CSV export
│   ├── analysis.py             ← Key frequency, KPM charts (matplotlib)
│   ├── auth.py                 ← Password hashing + session token management
│   └── requirements.txt        ← Python dependencies
│
├── frontend/                   ← Pure HTML / CSS / JavaScript UI
│   ├── index.html              ← Login page + full dashboard (single-page)
│   ├── css/
│   │   └── style.css           ← Dark cyberpunk theme
│   └── js/
│       └── app.js              ← WebSocket live feed, REST calls, charts, tabs
│
├── data/                       ← Auto-created at runtime
│   ├── keylog.enc              ← Fernet-encrypted keystroke log
│   ├── .key                    ← Encryption key (keep secret!)
│   └── .creds                  ← Hashed password file
│
├── tests/
│   └── test_demo.py            ← Unit tests
│
├── start.bat                   ← One-click Windows startup script
├── README.md                   ← This file
└── report.md                   ← Cybersecurity education report
🚀 Quick Start
1. Prerequisites
Python 3.10+ — Download
A modern browser (Chrome / Edge / Firefox)
2. Install Dependencies
cd "Keystroke Logging Demonstration\backend"
pip install -r requirements.txt
3. Start the Backend Server
python main.py
Or double-click start.bat for automatic startup.

You should see:

=================================================================
  ⚠️  KEYSTROKE LOGGING DEMONSTRATION SYSTEM  ⚠️
  FOR EDUCATIONAL & ETHICAL CYBERSECURITY USE ONLY
  Default login password: demo1234
  Open frontend/index.html in your browser
=================================================================
4. Open the Frontend
Open frontend/index.html in your browser (just double-click it).

The frontend is a static HTML file — no web server needed for it.

5. Login
Enter the default password: demo1234

🎯 Features
Feature	Description
🔐 Password Login	SHA-256 hashed + session tokens
⌨️ Live Keystroke Feed	WebSocket real-time stream
📊 Frequency Charts	Top 15 keys bar chart
⚡ KPM Over Time	Typing speed line chart
🥧 Key Distribution	Regular vs. Special key pie chart
💾 Encrypted Storage	Fernet symmetric encryption
📁 CSV Export	Download full keystroke log
🗑 Clear Data	Permanently wipe the log
🔑 Change Password	Update via dashboard
🛑 Explicit Start Only	No background/hidden logging
🔌 API Endpoints
Method	Endpoint	Description
POST	/api/login	Authenticate, get session token
POST	/api/logout	Revoke session
POST	/api/logger/start	Start keystroke logging
POST	/api/logger/stop	Stop keystroke logging
POST	/api/logger/reset	Stop + clear live session
GET	/api/logger/status	Running status + counts
GET	/api/keystrokes?n=100	Last N live keystrokes
GET	/api/stats	Aggregate statistics
GET	/api/charts	Base64 chart images (JSON)
GET	/api/export/csv	Download CSV report
WS	/ws/live?token=…	WebSocket real-time feed
Interactive API docs: http://localhost:8000/docs

🔒 Security & Encryption
Password is stored as a salted SHA-256 hash — never in plain text
Session Tokens are time-limited (1 hour TTL) and invalidated on logout
Keystroke data is encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
The .key file is stored locally — do not share it or the data can be decrypted
All endpoints (except /api/health) require a valid session token
🧪 Running Tests
cd "Keystroke Logging Demonstration"
python -m pytest tests/test_demo.py -v
📦 Tech Stack
Layer	Technology
Language	Python 3.10+
Backend Framework	FastAPI + Uvicorn
Keystroke Capture	pynput
Encryption	cryptography (Fernet)
Data Analysis	pandas, matplotlib, seaborn
Frontend	HTML5, CSS3, Vanilla JS
Real-time	WebSockets
Serialization	JSON + CSV
⚠️ Ethical Guidelines
Consent is mandatory — Only use on systems you own or have explicit written permission to monitor
No background operation — Logging only starts when the user clicks "Start Logging"
No data exfiltration — All data stays local; no network transmission beyond localhost
No stealth features — The UI is always visible; no system tray hiding
Educational context only — Intended for classroom, lab, and security awareness training
📄 Further Reading
See report.md for a detailed cybersecurity education report covering:

What is keylogging?
How attackers misuse it
Detection techniques
Prevention strategies
