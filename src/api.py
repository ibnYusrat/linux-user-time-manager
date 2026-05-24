from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
import json
import os
import subprocess
from datetime import datetime, timedelta
from functools import wraps
import pwd
import grp
import re
import pyotp
import qrcode
import io
import base64

import socket

app = Flask(__name__)

CONFIG_PATH = "/etc/user-time-manager/config.json"
CRED_PATH = "/etc/user-time-manager/credentials.json"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"users": {}}
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def load_creds():
    if not os.path.exists(CRED_PATH):
        # Generate a new secret if it doesn't exist
        secret = pyotp.random_base32()
        creds = {"totp_secret": secret, "totp_verified": False}
        save_creds(creds)
        return creds
    with open(CRED_PATH, 'r') as f:
        return json.load(f)

def save_creds(creds):
    with open(CRED_PATH, 'w') as f:
        json.dump(creds, f, indent=4)

def verify_totp(code):
    creds = load_creds()
    secret = creds.get('totp_secret')
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def get_non_admin_users():
    users = []
    for p in pwd.getpwall():
        if p.pw_uid >= 1000 and p.pw_uid < 65534:
            try:
                if 'sudo' not in [g.gr_name for g in grp.getgrall() if p.pw_name in g.gr_mem]:
                    users.append(p.pw_name)
            except:
                users.append(p.pw_name)
    return users

def get_usage_from_logs(username):
    today_str = datetime.now().strftime("%Y-%m-%d")
    total_mins = 0
    try:
        output = subprocess.check_output(["last", "-F", username], text=True)
        for line in output.splitlines():
            if not line.strip() or username not in line:
                continue
            parts = line.split()
            if len(parts) < 10: continue
            try:
                start_date_str = f"{parts[4]} {parts[5]} {parts[7]}" 
                if datetime.strptime(start_date_str, "%b %d %Y").strftime("%Y-%m-%d") != today_str:
                    continue
            except:
                continue
            if "still logged in" in line:
                full_start_str = " ".join(parts[3:8])
                start_time = datetime.strptime(full_start_str, "%a %b %d %H:%M:%S %Y")
                delta = datetime.now() - start_time
                total_mins += int(delta.total_seconds() / 60)
            elif "(" in line and ")" in line:
                match = re.search(r"\((\d+):(\d+)\)", line)
                if match:
                    hours, mins = map(int, match.groups())
                    total_mins += hours * 60 + mins
    except:
        pass
    return total_mins

@app.route('/')
def index():
    creds = load_creds()
    if not creds.get('totp_verified'):
        return redirect(url_for('setup_2fa'))

    config = load_config()
    if "users" not in config:
        config["users"] = {}
        
    non_admins = get_non_admin_users()
    changed = False
    for u in non_admins:
        if u not in config['users']:
            config['users'][u] = {
                "start_time": "0600",
                "end_time": "1800",
                "exception_until": None,
                "daily_usage": {}
            }
            changed = True
    if changed:
        save_config(config)

    display_users = []
    today = datetime.now().strftime("%Y-%m-%d")
    for u, user_data in config['users'].items():
        if u in non_admins:
            user_data["username"] = u
            if "daily_usage" not in user_data:
                user_data["daily_usage"] = {}
            usage_mins = user_data["daily_usage"].get(today, 0)
            if usage_mins == 0:
                usage_mins = get_usage_from_logs(u)
            user_data["usage_today_formatted"] = f"{usage_mins // 60}h {usage_mins % 60}m"
            user_data["usage_mins"] = usage_mins
            
            # Format exception for UI
            user_data["has_exception"] = False
            user_data["exception_time"] = ""
            if user_data.get("exception_until"):
                try:
                    expiry = datetime.fromisoformat(user_data["exception_until"])
                    if expiry > datetime.now():
                        user_data["has_exception"] = True
                        user_data["exception_time"] = expiry.strftime("%H:%M")
                except:
                    pass
            
            display_users.append(user_data)
            
    return render_template('index.html', users=display_users)

@app.route('/setup')
def setup_2fa():
    creds = load_creds()
    if creds.get('totp_verified'):
        return redirect(url_for('index'))
    return render_template('setup.html')

@app.route('/api/verify_setup', methods=['POST'])
def verify_setup():
    data = request.json
    code = data.get('code')
    if verify_totp(code):
        creds = load_creds()
        creds['totp_verified'] = True
        save_creds(creds)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid code. Try again."}), 401

@app.route('/api/extend', methods=['POST'])
def extend_time():
    data = request.json
    code = data.get('code')
    if not verify_totp(code):
        return jsonify({"status": "error", "message": "Invalid 2FA Code"}), 401

    username = data.get('username')
    minutes = int(data.get('minutes', 60))
    
    config = load_config()
    if username in config['users']:
        now = datetime.now()
        current_expiry = config['users'][username].get('exception_until')
        start_from = now
        if current_expiry:
            try:
                expiry_dt = datetime.fromisoformat(current_expiry)
                if expiry_dt > now:
                    start_from = expiry_dt
            except:
                pass
        
        new_expiry = start_from + timedelta(minutes=minutes)
        config['users'][username]['exception_until'] = new_expiry.isoformat()
        save_config(config)
        return jsonify({"status": "success", "new_expiry": new_expiry.strftime("%H:%M")})
    
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/api/update_schedule', methods=['POST'])
def update_schedule():
    data = request.json
    code = data.get('code')
    if not verify_totp(code):
        return jsonify({"status": "error", "message": "Invalid 2FA Code"}), 401

    username = data.get('username')
    start = data.get('start_time')
    end = data.get('end_time')
    
    config = load_config()
    if username in config['users']:
        if start:
            config['users'][username]['start_time'] = start.replace(":", "")
        if end:
            config['users'][username]['end_time'] = end.replace(":", "")
        save_config(config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/api/qr')
def get_qr():
    creds = load_creds()
    if creds.get('totp_verified'):
        return "Setup already complete", 403
        
    secret = creds.get('totp_secret')
    if not secret:
        return "Not configured", 404
    
    hostname = socket.gethostname()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=f"Admin@{hostname}", 
        issuer_name=f"Time Manager ({hostname})"
    )
    
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
