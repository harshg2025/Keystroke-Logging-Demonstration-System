# 📄 Cybersecurity Education Report
## Keystroke Logging — Understanding, Detection & Prevention

> **Document Type:** Educational Reference | **Audience:** Students, Developers, Security Professionals
> **⚠️ For Academic & Ethical Use Only**

---

## 1. What is Keystroke Logging (Keylogging)?

A **keystroke logger** (keylogger) is a type of surveillance software — or hardware — that records every key pressed on a keyboard. The recorded data can include:

- Typed text (emails, passwords, documents)
- Application focus events (which app was active)
- Mouse clicks (in advanced variants)
- Screenshots taken at intervals (in advanced variants)

Keyloggers operate at different system levels:

| Level | Mechanism | Example |
|---|---|---|
| **Application** | Hooks into OS event queue | Python pynput, AutoHotKey |
| **Kernel/Driver** | OS-level driver filter | Rootkit-based keyloggers |
| **Hardware** | Physical USB/PS2 dongle | KeyGrabber USB |
| **Hypervisor** | Virtual machine monitor | Academic research only |
| **Acoustic** | Keystroke sound analysis | Side-channel attack |
| **Electromagnetic** | EM emissions from keyboard | NSA-class tools |

This demonstration uses **Application-level** logging only — the shallowest and most detectable form.

---

## 2. How Attackers Misuse Keyloggers

### 2.1 Credential Theft
The most common attack vector. Attackers capture:
- Bank login credentials
- Email / social media passwords
- VPN / remote desktop passwords
- Cryptocurrency wallet passphrases

### 2.2 Corporate Espionage
Deployed on employee machines to capture:
- Trade secrets typed in documents
- Internal communications
- Source code and IP

### 2.3 Surveillance & Stalkerware
Used by abusers to monitor victims:
- Domestic abuse scenarios
- Stalking ex-partners
- Unauthorized employer monitoring

### 2.4 Malware Payloads
Often bundled with:
- Trojans (e.g., Emotet, TrickBot)
- RATs (Remote Access Trojans)
- Ransomware droppers (initial recon phase)

### 2.5 Real-World Examples
| Attack | Year | Impact |
|---|---|---|
| Zeus Trojan | 2007–2010 | $100M+ stolen via banking keyloggers |
| Spyeye | 2009–2012 | 1.4M computers infected |
| Agent Tesla | 2014–present | Active credential-stealing RAT |
| Snake Keylogger | 2020–present | Targets Windows via phishing |

---

## 3. Detection Techniques

### 3.1 Antivirus / EDR Detection
- Behavioral heuristics flag `keyboard hook` API calls (`SetWindowsHookEx`)
- Signature-based detection of known keylogger binaries
- Memory scanning for hook tables

### 3.2 Process Monitoring
```
# Windows: Check for suspicious keyboard hooks
Get-Process | Where-Object { $_.Modules | Where-Object { $_.ModuleName -like "*hook*" } }
```

Look for processes:
- Running as SYSTEM with keyboard access
- Loading keyboard filter drivers
- With no visible window (hidden processes)

### 3.3 Network Traffic Analysis
Application-level keyloggers exfiltrate data by:
- Emailing logs to attacker (SMTP)
- Uploading via FTP/HTTP
- Using Telegram/Discord bots (modern)

Monitor for:
- Unexpected outbound SMTP connections
- Periodic small uploads to unknown IPs
- DNS queries to newly-registered domains

### 3.4 File System Indicators
Look for:
- Auto-start registry keys: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Suspicious files in `%AppData%`, `%Temp%`, `%ProgramData%`
- Files with `.log`, `.dat`, `.enc` extensions being modified in real-time

### 3.5 This Demo's Detection Footprint
This educational logger would be detected because:
- ✅ Runs as a visible window (not hidden)
- ✅ Registered as a Python process (not obfuscated)
- ✅ pynput uses documented OS APIs (flagged by AV)
- ✅ Stores data locally (no exfiltration)
- ✅ Requires explicit user start (no persistence)

---

## 4. Prevention Strategies

### 4.1 For End Users
| Strategy | Implementation |
|---|---|
| **Use a Password Manager** | Autofill bypasses keyboard input entirely |
| **Virtual Keyboard** | On-screen keyboard avoids key-press events |
| **Two-Factor Authentication** | Even captured passwords are useless without 2FA |
| **Keep AV Updated** | Modern EDR solutions catch 95%+ of known keyloggers |
| **OS Updates** | Patch kernel vulnerabilities that allow deep hooks |
| **Run as Standard User** | Limits keylogger privilege escalation |

### 4.2 For Developers
- **Never log password fields** — check `input[type=password]` or equivalent
- **Use secure input APIs** — Windows `SecureString`, Linux `/dev/input` with permissions
- **Encrypt sensitive in-memory data** — zero-out buffers after use
- **Code signing** — makes it harder to slip keyloggers into supply chains

### 4.3 For Organizations
- **Endpoint Detection & Response (EDR)** — CrowdStrike, SentinelOne, Microsoft Defender for Endpoint
- **User Entity Behavior Analytics (UEBA)** — Detects anomalous typing patterns
- **Network DLP** — Prevents log exfiltration
- **Application Whitelisting** — Only allow approved executables

### 4.4 For High-Security Environments
- **Hardware Security Modules (HSM)** — PIN entered directly on tamper-proof device
- **Air-gapped systems** — No network for data exfiltration
- **TEMPEST shielding** — Blocks electromagnetic emissions
- **Biometric authentication** — No keystrokes to capture

---

## 5. Legal Perspective

### When Is Keylogging Legal?
| Scenario | Legal? | Notes |
|---|---|---|
| Monitoring your own device | ✅ Yes | |
| Parental controls (with child's knowledge) | ✅ Generally | Varies by jurisdiction |
| Employer monitoring (with policy notice) | ✅ Yes | Must be disclosed |
| Security research (in isolated lab) | ✅ Yes | With proper ethics approval |
| Monitoring others without consent | ❌ No | Criminal offence in most countries |
| Installing on someone's device covertly | ❌ No | Computer Fraud and Abuse Act (US), Computer Misuse Act (UK), IT Act (India) |

### Key Laws
- 🇺🇸 **Computer Fraud and Abuse Act (CFAA)** — Up to 10 years imprisonment
- 🇬🇧 **Computer Misuse Act 1990** — Up to 10 years imprisonment
- 🇮🇳 **IT Act 2000 (Section 66)** — Up to 3 years imprisonment + fine
- 🇪🇺 **GDPR** — Heavy fines for unauthorized data collection

---

## 6. How This Demonstration Works

```
┌─────────────────────────────────────────────────────────────┐
│                  USER presses a key                         │
└────────────────────────┬────────────────────────────────────┘
                         │ pynput OS hook (application level)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               logger.py  – KeystrokeLogger                  │
│  • Labels the key  (e.g. "a", "[SPACE]", "[ENTER]")        │
│  • Timestamps it (Unix epoch)                               │
│  • Adds to in-memory ring buffer (max 500 keys)             │
└────────┬──────────────────────────┬─────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐    ┌──────────────────────────────────────┐
│  storage.py     │    │  WebSocket broadcast to all clients  │
│  Fernet encrypt │    │  (asyncio Queue per WS connection)   │
│  → keylog.enc   │    └───────────────┬──────────────────────┘
└─────────────────┘                    │
                                       ▼
                         ┌─────────────────────────┐
                         │   Browser frontend       │
                         │   Live keystroke feed    │
                         └─────────────────────────┘
```

---

## 7. Glossary

| Term | Definition |
|---|---|
| **API Hook** | Intercepting OS function calls to monitor input |
| **Fernet** | Symmetric encryption using AES-128-CBC + HMAC-SHA256 |
| **pynput** | Python library for monitoring/controlling keyboards and mice |
| **WebSocket** | Full-duplex communication channel over TCP |
| **EDR** | Endpoint Detection and Response — advanced AV for enterprises |
| **RAT** | Remote Access Trojan — malware giving attackers full system control |
| **Exfiltration** | Unauthorized transfer of data from a victim's system |
| **TEMPEST** | NATO standard for preventing electromagnetic data leakage |

---

## 8. References

1. Ortolani, S. et al. (2011). *ShadowSafe: Operating System-Independent Keylogger Detection*. IEEE Symposium on Security and Privacy.
2. Miluzzo, E. et al. (2012). *Tapprints: Your Finger Taps Have Fingerprints*. ACM MobiSys.
3. OWASP (2023). *Testing for Sensitive Information in Browser Storage*. OWASP Testing Guide v4.2.
4. NIST (2022). *SP 800-63B: Digital Identity Guidelines — Authentication and Lifecycle Management*.
5. Cimpanu, C. (2020). *Snake Keylogger malware analysis*. ZDNet Security Research.

---

*Document prepared for educational and academic purposes only. — Keystroke Logging Demonstration System v1.0*
