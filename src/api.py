from flask import Flask, render_template, request, jsonify, Response
import json
import os
import pwd
import grp
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
CONFIG_PATH = "/etc/user-time-manager/config.json"
CRED_PATH = "/etc/user-time-manager/credentials.json"

def get_non_admin_users():
    try:
        sudo_users = grp.getgrnam('sudo').gr_mem
    except KeyError:
        sudo_users = []
        
    users = []
    for p in pwd.getpwall():
        if 1000 <= p.pw_uid < 60000 and p.pw_name not in sudo_users and p.pw_name != 'nobody':
            users.append(p.pw_name)
    return users

def get_credentials():
    try:
        with open(CRED_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {"username": "admin", "password": "admin123"}

def check_auth(username, password):
    creds = get_credentials()
    return username == creds.get("username", "admin") and password == creds.get("password", "admin123")

def authenticate():
    return Response('Authentication required.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

import re
import subprocess

def get_usage_from_logs(username):
    """Attempt to recover today's usage from system logs (last command)."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    total_mins = 0
    try:
        # last -F gives full date/time stamps
        output = subprocess.check_output(["last", "-F", username], text=True)
        for line in output.splitlines():
            if not line.strip() or username not in line:
                continue
            
            # Check if session started today
            # Format: username tty7 :0 Fri May 22 17:08:49 2026 ...
            parts = line.split()
            if len(parts) < 10: continue
            
            try:
                start_date_str = f"{parts[4]} {parts[5]} {parts[7]}" # May 22 2026
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
@requires_auth
def index():
    config = load_config()
    if "users" not in config:
        config["users"] = {}
        
    non_admins = get_non_admin_users()
    changed = False
    
    # Auto-add newly discovered non-admin users with a default schedule
    for u in non_admins:
        if u not in config['users']:
            config['users'][u] = {
                "start_time": "0600",
                "end_time": "1800",
                "exception_until": None
            }
            changed = True
            
    if changed:
        save_config(config)
        
    # Only send actual non-admin users to the frontend template
    display_users = {}
    today = datetime.now().strftime("%Y-%m-%d")
    
    for u in non_admins:
        if u in config['users']:
            user_data = config['users'][u].copy()
            if "daily_usage" not in user_data:
                user_data["daily_usage"] = {}
            
            usage_mins = user_data["daily_usage"].get(today, 0)
            
            # If tracking just started or data is missing, try log recovery
            if usage_mins == 0:
                usage_mins = get_usage_from_logs(u)
                # Save it back to config so sweep can increment from here
                if usage_mins > 0:
                    if "daily_usage" not in config['users'][u]:
                        config['users'][u]["daily_usage"] = {}
                    config['users'][u]["daily_usage"][today] = usage_mins
                    changed = True

            user_data["usage_today_formatted"] = f"{usage_mins // 60}h {usage_mins % 60}m"
            user_data["usage_mins"] = usage_mins
            display_users[u] = user_data
            
    if changed:
        save_config(config)
            
    return render_template('index.html', users=display_users)

@app.route('/api/extend', methods=['POST'])
@requires_auth
def extend_time():
    data = request.json
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

@app.route('/api/reset', methods=['POST'])
@requires_auth
def reset_time():
    data = request.json
    username = data.get('username')
    config = load_config()
    if username in config['users']:
        config['users'][username]['exception_until'] = None
        save_config(config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

@app.route('/api/update_schedule', methods=['POST'])
@requires_auth
def update_schedule():
    data = request.json
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
    return jsonify({"status": "error"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
