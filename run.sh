#!/bin/bash

rm -rf ~/printer_data/logs/klippy.log
touch ~/printer_data/logs/klippy.log
chown pi:pi ~/printer_data/logs/klippy.log
chmod 666 ~/printer_data/logs/klippy.log

rm -rf ~/logs/theos.log
touch ~/logs/theos.log
chown pi:pi ~/logs/theos.log
chmod 666 ~/logs/theos.log

cd ~/klipper/
git checkout develop
git reset --hard origin/develop
git pull

cd ~/THE100-Configuration/
git checkout develop
git pull

git reset f79fe5e --hard
git pull
./scripts/install-configuration.sh 