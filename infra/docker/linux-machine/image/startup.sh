#!/bin/bash

mkdir -p /var/run/sshd

chown -R root:root /root
mkdir -p /root/.config/pcmanfm/LXDE/

# Set VNC password if provided
if [ -n "$VNC_PASSWORD" ]; then
    echo -n "$VNC_PASSWORD" > /.password1
    x11vnc -storepasswd $(cat /.password1) /.password2
    chmod 400 /.password*
    sed -i 's/^command=x11vnc.*/& -rfbauth \/.password2/' /etc/supervisor/conf.d/supervisord.conf
    export VNC_PASSWORD=
fi

# Start nginx
nginx -c /etc/nginx/nginx.conf

# Start supervisor
exec /bin/tini -- /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf