#!/bin/bash
rm -rf ~/logs/theos.log
touch ~/logs/theos.log
chown pi:pi ~/logs/theos.log
chmod 666 ~/logs/theos.log
git reset cd8a284 --hard
git pull
./scripts/install-configuration.sh 