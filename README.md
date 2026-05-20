# 🐧 Linux Family Time Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-lightgrey.svg)]()
[![Python 3.x](https://img.shields.io/badge/Python-3.x-yellow.svg)]()

**Linux Family Time Manager** is a robust, zero-configuration parental control and screen-time management solution built exclusively for Linux desktop environments (Ubuntu, Linux Mint, Debian, Arch, etc.). 

Designed as an open-source alternative to proprietary solutions like *Microsoft Family Safety* or *Google Family Link*, this tool gives parents complete, airtight control over when their children can log in, while offering the flexibility of a mobile-friendly web dashboard to grant remote exceptions on the fly.

---

## ✨ Key Features

*   🛡️ **Airtight PAM Enforcement:** Integrates directly into Linux's Pluggable Authentication Modules (`pam_exec.so`). It blocks logins at the system level before the desktop environment even loads.
*   🧹 **Active Session Sweeping:** Automatically kicks users out if they are actively playing a game or watching a video when their allowed time window expires.
*   📱 **Remote Web Dashboard:** A mobile-friendly Flask web portal allows parents to grant bonus time (e.g., "+1 Hour" or "+15 Mins") instantly from their smartphone.
*   ⏱️ **Dynamic Schedule Management:** Set permanent start and end times for each child directly from the web UI.
*   🕵️ **Zero-Configuration Auto-Discovery:** Automatically scans your system and detects non-admin child accounts. No manual configuration files required!
*   🔒 **Administrator Fail-Safe:** Hardcoded safeguards ensure that accounts in the `sudo` group can **never** be locked out, preventing accidental system lockouts.
*   🛑 **BIOS Cheat Prevention:** Forces the GUI (LightDM/GDM) to wait for a verified Network Time Protocol (NTP) sync before allowing logins, completely preventing children from bypassing restrictions by modifying the motherboard hardware clock.

---

## 🏗️ How It Works

Unlike simple `cron` scripts that can be easily bypassed, Linux Family Time Manager uses a multi-layered security architecture:

1.  **The Database:** A single source of truth located at `/etc/user-time-manager/config.json`.
2.  **The Front Door:** `pam_check.py` evaluates all login attempts against the schedule and active exceptions.
3.  **The Enforcer:** A background cron job (`sweep.sh`) runs every 15 minutes, warning users with a desktop notification before forcefully terminating expired sessions via `loginctl`.
4.  **The API:** A lightweight Python/Flask web server (`api.py`) runs as a `systemd` service, allowing parents to securely modify the database from any device on the local network.

---

## 🚀 Installation

Installation takes less than 30 seconds.

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/linux-family-time-manager.git
   cd linux-family-time-manager
   ```

2. Run the automated installer as root:
   ```bash
   sudo ./install.sh
   ```

The installer automatically detects your Python path, installs required dependencies (`python3-flask`), configures PAM, and registers the background services.

---

## 📱 Usage & Configuration

Once installed, grab your phone or another computer on the same Wi-Fi network and open your browser:

**URL:** `http://<YOUR_LINUX_PC_IP_ADDRESS>:5000`

### Default Login
The web dashboard is protected by HTTP Basic Authentication.
*   **Username:** `admin`
*   **Password:** `admin123`

### Changing the Password
For security, change the default password immediately. Edit the secure credentials file on your Linux machine:
```bash
sudo nano /etc/user-time-manager/credentials.json
```
Changes take effect instantly. No service restart required.

### Managing Kids
*   **Schedules:** Use the time pickers on the dashboard to set the permanent allowed window (e.g., `06:00` to `18:00`).
*   **Bonus Time:** Tap "+1 Hour" or "+15 Mins" to grant temporary exceptions. The system handles the math and automatically revokes access when the time expires.
*   **Adding Kids:** Simply create a standard Linux user account on your machine. The dashboard will automatically discover them on the next refresh!

---

## 🔐 Security Recommendations

To make this system 100% foolproof against tech-savvy teenagers:
1.  **Set a BIOS Password:** Prevent them from booting from a live USB or altering hardware settings.
2.  **Lock Polkit Time Settings:** Ensure they cannot change the system time from within Linux. (Most modern desktop environments restrict this by default, but it is worth verifying).

---

## 💻 Tech Stack
*   **Language:** Python 3, Bash
*   **Web Framework:** Flask
*   **System Integration:** systemd, PAM (`pam_exec`), cron, loginctl, DBus (for notifications)

*Keywords: Linux Parental Controls, Ubuntu Screen Time, Linux Mint Family Safety, Google Family Link Alternative, Pluggable Authentication Modules, PAM login restriction, Systemd time restriction, Linux parental lock.*