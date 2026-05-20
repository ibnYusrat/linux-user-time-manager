import sys
import json
import os
from datetime import datetime, timedelta

CONFIG_PATH = "/etc/user-time-manager/config.json"

def check_access(username):
    # 1. Load configuration
    if not os.path.exists(CONFIG_PATH):
        return True # Default to allow if config missing to prevent lockout
        
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    except:
        return True

    user_config = config.get("users", {}).get(username)
    if not user_config:
        return True # Not a restricted user

    now = datetime.now()
    curr_time = now.strftime("%H%M")
    curr_val = int(curr_time)

    # 2. Check standard time window
    start_val = int(user_config.get("start_time", "0000"))
    end_val = int(user_config.get("end_time", "2359"))
    
    is_in_window = False
    if start_val < end_val:
        if start_val <= curr_val < end_val:
            is_in_window = True
    else: # Crosses midnight
        if curr_val >= start_val or curr_val < end_val:
            is_in_window = True

    if is_in_window:
        return True

    # 3. Check for active exceptions
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
    # PAM passes the username as an environment variable or argument
    # For pam_exec, it is often via PAM_USER env var
    user = os.environ.get("PAM_USER")
    if not user and len(sys.argv) > 1:
        user = sys.argv[1]

    if not user:
        sys.exit(0)

    if check_access(user):
        sys.exit(0) # Success
    else:
        sys.exit(1) # Failure
