#!/usr/bin/env sh

sudo yes | cp -f etc/supervisor/conf.d/asgi.conf /etc/supervisor/conf.d/asgi.conf
sudo yes | cp -f etc/supervisor/conf.d/rrtelebot.conf /etc/supervisor/conf.d/rrtelebot.conf

sudo supervisorctl update all
