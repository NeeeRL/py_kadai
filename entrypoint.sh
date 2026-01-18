#!/bin/bash
rm -f /tmp/.X1-lock
Xvfb :1 -screen 0 1024x768x24 > /dev/null 2>&1 &
sleep 2
fluxbox > /dev/null 2>&1 &
x11vnc -display :1 -passwd 1234 -forever -shared -rfbport 5901 > /dev/null 2>&1 &
exec "$@"
