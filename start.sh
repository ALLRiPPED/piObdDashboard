#!/bin/bash
cd /home/pi/piObdDashboard
/home/pi/.config/nvm/versions/node/v14.16.0/bin/node index.js & #adjust path to node installation dir
sleep 3 #give enough time for node server to start
python3 tempMonitor.py &
python3 obdDash.py &
chromium-browser --window-position=0,0 --kiosk
unclutter -idle 1 &
