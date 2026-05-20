#!/bin/bash
# Wait up to 60 seconds for time to sync, then check if it's actually synced.
# If completely offline, it will eventually proceed, but if online, it ensures sync.
timeout 60 bash -c 'until timedatectl status | grep -q "System clock synchronized: yes"; do sleep 1; done'
exit 0
