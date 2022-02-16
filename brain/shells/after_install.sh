#!/bin/bash

sudo touch /home/pi/brain/shells/after_install.log
sudo chown pi /home/pi/brain/shells/after_install.log
# redirect stdout/stderr to a file
exec >after_install.log 2>&1

sudo chown pi /home/pi/brain/src/command/version.py
. ~/venv/bin/activate && pip3 install /home/pi/brain/.
sudo /sbin/shutdown -r +1

exit
