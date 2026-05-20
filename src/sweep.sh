#!/bin/bash
# Active session sweep and termination
# Reads from the central /etc/user-time-manager/config.json

CONFIG_PATH="/etc/user-time-manager/config.json"

if [ ! -f "$CONFIG_PATH" ]; then
    exit 0
fi

# We can use python to quickly parse the JSON and check all users
/usr/bin/python3 - << 'EOF'
import json
import os
import pwd
import grp
import subprocess
from datetime import datetime, timedelta

CONFIG_PATH = "/etc/user-time-manager/config.json"

try:
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
except Exception:
    exit(0)

now = datetime.now()
curr_val = int(now.strftime("%H%M"))

try:
    sudo_users = grp.getgrnam('sudo').gr_mem
except:
    sudo_users = []

for username, user_config in config.get("users", {}).items():
    # HARD FAILSAFE: Never log out administrators
    if username == 'root' or username in sudo_users:
        continue
    try:
        p = pwd.getpwnam(username)
        if p.pw_uid < 1000:
            continue
    except:
        continue

    # 1. Check standard window
    start_val = int(user_config.get("start_time", "0000"))
    end_val = int(user_config.get("end_time", "2359"))
    
    is_in_window = False
    if start_val < end_val:
        if start_val <= curr_val < end_val:
            is_in_window = True
    else:
        if curr_val >= start_val or curr_val < end_val:
            is_in_window = True

    # 2. Check exceptions
    has_exception = False
    exception_until = user_config.get("exception_until")
    if exception_until:
        try:
            until_dt = datetime.fromisoformat(exception_until)
            if now < until_dt:
                has_exception = True
        except:
            pass

    # If they are NOT in window and DO NOT have an exception, kick them out
    if not is_in_window and not has_exception:
        try:
            user_id = subprocess.check_output(['id', '-u', username]).decode('utf-8').strip()
            if subprocess.call(['pgrep', '-u', user_id], stdout=subprocess.DEVNULL) == 0:
                dbus_pid = subprocess.check_output(f"pgrep -u {user_id} -x xfce4-session || pgrep -u {user_id} -x systemd | head -n 1", shell=True).decode('utf-8').strip()
                
                if dbus_pid:
                    env_raw = subprocess.check_output(['cat', f'/proc/{dbus_pid}/environ']).decode('utf-8', errors='ignore')
                    dbus_addr = None
                    for line in env_raw.split('\0'):
                        if line.startswith('DBUS_SESSION_BUS_ADDRESS='):
                            dbus_addr = line.split('=', 1)[1]
                            break
                    
                    if dbus_addr:
                        cmd = f"sudo -u {username} DBUS_SESSION_BUS_ADDRESS={dbus_addr} notify-send -u critical -t 10000 'Time Limit Reached' 'Your allowed time frame has ended.\\n\\nLogging out in 10 seconds...'"
                        subprocess.call(cmd, shell=True)
                        subprocess.call(['sleep', '10'])
                
                subprocess.call(['loginctl', 'terminate-user', username])
        except Exception as e:
            pass
EOF
