#!/bin/bash
# Install script for Linux User Time Manager

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

PROJECT_DIR=$(pwd)
INSTALL_DIR="/opt/user-time-manager"
CONFIG_DIR="/etc/user-time-manager"

PYTHON_PATH=$(which python3)
echo "Using Python at: $PYTHON_PATH"

echo "Setting up directories..."
mkdir -p "$INSTALL_DIR/templates"
mkdir -p "$CONFIG_DIR"

echo "Copying files..."
cp src/pam_check.py "$INSTALL_DIR/"
cp src/api.py "$INSTALL_DIR/"
cp src/templates/index.html "$INSTALL_DIR/templates/"

# Create initial config if not exists
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo '{"users": {}}' > "$CONFIG_DIR/config.json"
fi

chown -R root:root "$INSTALL_DIR"
chown -R root:root "$CONFIG_DIR"
chmod 644 "$CONFIG_DIR/config.json"
chmod 600 "$CONFIG_DIR/credentials.json"

echo "Installing systemd service for API..."
cat << EOF > /etc/systemd/system/user-time-api.service
[Unit]
Description=User Time Manager API
After=network.target

[Service]
ExecStart=$PYTHON_PATH $INSTALL_DIR/api.py
Restart=always
User=root
WorkingDirectory=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable user-time-api.service
systemctl start user-time-api.service

echo "Installing sweep cron job..."
cp src/sweep.sh "$INSTALL_DIR/"
# Update the python path inside sweep.sh
sed -i "s|/usr/bin/python3|$PYTHON_PATH|g" "$INSTALL_DIR/sweep.sh"
chmod +x "$INSTALL_DIR/sweep.sh"
echo "*/5 * * * * root $INSTALL_DIR/sweep.sh" > /etc/cron.d/user-time-sweep
chmod 644 /etc/cron.d/user-time-sweep

echo "Configuring PAM..."
# Backup common-account
cp /etc/pam.d/common-account /etc/pam.d/common-account.bak

# Check if already installed
if ! grep -q "pam_check.py" /etc/pam.d/common-account; then
    # Add our check before pam_permit/pam_deny
    # We want it to be 'requisite' so it fails immediately if the script exits 1
    sed -i "/account required pam_time.so/a account [success=ok ignore=ignore default=bad] pam_exec.so stdout quiet $PYTHON_PATH $INSTALL_DIR/pam_check.py" /etc/pam.d/common-account
else
    # Update existing line if python path changed
    sed -i "s|pam_exec.so .* pam_check.py|pam_exec.so stdout quiet $PYTHON_PATH $INSTALL_DIR/pam_check.py|g" /etc/pam.d/common-account
fi

echo "Cleaning up old hack files..."
rm -f /etc/cron.d/enforce-time-sweep
rm -f /etc/security/time_msg
sed -i "/account required pam_time.so/d" /etc/pam.d/common-account

echo "Installation complete. API running on port 5000."

echo "Configuring Boot-Time Network Sync Enforcement..."
# Copy the strict sync script
cp src/strict-time-sync.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/strict-time-sync.sh"

# Enable the built-in systemd time wait service
systemctl enable systemd-time-wait-sync.service

# Create the LightDM override to force it to wait for time sync
mkdir -p /etc/systemd/system/lightdm.service.d/
cat << OVERRIDE > /etc/systemd/system/lightdm.service.d/override.conf
[Unit]
After=systemd-time-wait-sync.service NetworkManager-wait-online.service network-online.target
Wants=systemd-time-wait-sync.service NetworkManager-wait-online.service network-online.target

[Service]
ExecStartPre=$INSTALL_DIR/strict-time-sync.sh
OVERRIDE

systemctl daemon-reload
echo "Boot sync enforcement configured."

echo "Installing required Python packages..."
apt-get install -y python3-flask
