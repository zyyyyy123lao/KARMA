rm -rf /tmp/.X1* /root/.vnc/*.log
USER=root /opt/TurboVNC/bin/vncserver :1 \
  -desktop X \
  -auth /root/.Xauthority \
  -geometry 1920x1080 \
  -depth 24 \
  -rfbwait 120000 \
  -rfbauth /root/.vnc/passwd \
  -fp /usr/share/fonts/X11/misc/,/usr/share/fonts \
  -rfbport 6006

export DISPLAY=:1