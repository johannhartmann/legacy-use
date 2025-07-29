#!/bin/bash

# Kill any existing VNC server
vncserver -kill :1 2>/dev/null || true

# Remove any existing lock files
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

# Start VNC server on port 5900 instead of 5901
Xtightvnc :1 \
    -desktop X \
    -auth /root/.Xauthority \
    -geometry ${VNCGEOMETRY:-1024x768} \
    -depth ${VNCDEPTH:-16} \
    -rfbwait 120000 \
    -rfbport 5900 \
    -fp /usr/share/fonts/X11/misc/,/usr/share/fonts/X11/Type1/,/usr/share/fonts/X11/75dpi/,/usr/share/fonts/X11/100dpi/ \
    -co /etc/X11/rgb &

# Wait for VNC to start
sleep 2

# Start the X session if xstartup exists
export DISPLAY=:1
if [ -f /root/.vnc/xstartup ]; then
    /root/.vnc/xstartup &
else
    # Simple X session
    xsetroot -solid grey &
fi

# Start DOSBox
if [ -f /usr/local/bin/startdosbox.sh ]; then
    /usr/local/bin/startdosbox.sh &
else
    # Fallback: start DOSBox directly
    /usr/bin/dosbox -conf /config/dosbox.conf &
fi

# Keep the container running
tail -f /dev/null