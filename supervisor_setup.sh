#!/usr/bin/env sh

yes | sudo cp -f etc/supervisor/conf.d/asgi.conf /etc/supervisor/conf.d/asgi.conf
yes | sudo cp -f etc/supervisor/conf.d/rrtelebot.conf /etc/supervisor/conf.d/rrtelebot.conf

sudo supervisorctl reread
sudo supervisorctl restart all
