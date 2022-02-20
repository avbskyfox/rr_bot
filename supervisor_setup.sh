#!/usr/bin/env sh

sudo su

yes | cp -f etc/supervisor/conf.d/asgi.conf /etc/supervisor/conf.d/asgi.conf
yes | cp -f etc/supervisor/conf.d/rrtelebot.conf /etc/supervisor/conf.d/rrtelebot.conf

supervisorctl update all
