import sys
import json
import os
import pwd
import grp
from datetime import datetime, timedelta

CONFIG_PATH = "/etc/user-time-manager/config.json"

def is_admin(username):
    if username == 'root': 
        return True
    try:
        p = pwd.getpwnam(username)
        if p.pw_uid < 1000: 
            return True
        if username in grp.getgrnam('sudo').gr_mem: 
            return True
    except:
        pass
    return False

def check_access(username):
    # HARD FAILSAFE: Never block administrators or system accounts
    if is_admin(username):
        return True

    if not os.path.exists(CONFIG_PATH):
        return True
        
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    except:
        return True

    user_config = config.get("users", {}).get(username)
    if not user_config:
        return True

    now = datetime.now()
    curr_time = now.strftime("%H%M")
    curr_val = int(curr_time)

    start_val = int(user_config.get("start_time", "0000"))
    end_val = int(user_config.get("end_time", "2359"))
    
    is_in_window = False
    if start_val < end_val:
        if start_val <= curr_val < end_val:
            is_in_window = True
    else: 
        if curr_val >= start_val or curr_val < end_val:
            is_in_window = True

    if is_in_window:
        return True

    exception_until = user_config.get("exception_until")
    if exception_until:
        try:
            until_dt = datetime.fromisoformat(exception_until)
            if now < until_dt:
                return True
        except:
            pass

    return False

if __name__ == "__main__":
    user = os.environ.get("PAM_USER")
    if not user and len(sys.argv) > 1:
        user = sys.argv[1]

    if not user:
        sys.exit(0)

    if check_access(user):
        sys.exit(0)
    else:
        sys.exit(1)
