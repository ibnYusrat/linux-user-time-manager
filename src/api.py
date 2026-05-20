from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CONFIG_PATH = "/etc/user-time-manager/config.json"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', users=config['users'])

@app.route('/api/extend', methods=['POST'])
def extend_time():
    data = request.json
    username = data.get('username')
    minutes = int(data.get('minutes', 60))
    
    config = load_config()
    if username in config['users']:
        now = datetime.now()
        # If there's already an active exception, extend from that time, otherwise from now
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
def reset_time():
    data = request.json
    username = data.get('username')
    config = load_config()
    if username in config['users']:
        config['users'][username]['exception_until'] = None
        save_config(config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
