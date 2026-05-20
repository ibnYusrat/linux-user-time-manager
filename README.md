# Linux User Time Manager

A robust, multi-layered system to restrict user login times and provide remote "bonus time" exceptions via a web API.

## Features
- **PAM-based Enforcement:** Real-time login blocking using `pam_exec`.
- **Dynamic Exceptions:** Grant extra time (e.g., +1 hour) remotely without editing system files.
- **Web Portal:** Simple mobile-friendly dashboard to manage users.
- **Auto-Sync:** Optionally waits for network time sync on boot to prevent BIOS clock cheating.

## Project Structure
- `src/pam_check.py`: The core engine that decides if a login is allowed.
- `src/api.py`: Flask-based web server for remote management.
- `src/templates/`: UI for the web portal.
- `install.sh`: Automated system integration script.

## Setup
1. `chmod +x install.sh`
2. `sudo ./install.sh`
3. Access the portal at `http://your-ip:5000`
