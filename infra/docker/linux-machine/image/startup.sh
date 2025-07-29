#!/bin/bash

mkdir -p /var/run/sshd

chown -R root:root /root
mkdir -p /root/.config/pcmanfm/LXDE/

# TightVNC is configured with no password (-SecurityTypes None)

# Start nginx
nginx -c /etc/nginx/nginx.conf

# Start supervisor
exec /bin/tini -- /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf