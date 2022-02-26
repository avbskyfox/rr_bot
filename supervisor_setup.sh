#!/usr/bin/env sh

yes | sudo cp -f etc/supervisor/conf.d/asgi.conf /etc/supervisor/conf.d/asgi.conf
yes | sudo cp -f etc/supervisor/conf.d/rrtelebot.conf /etc/supervisor/conf.d/rrtelebot.conf
yes | sudo cp -f etc/supervisor/conf.d/celery.conf /etc/supervisor/conf.d/celery.conf
yes | sudo cp -f etc/supervisor/conf.d/celery_prod.conf /etc/supervisor/conf.d/celery_prod.conf

sudo supervisorctl reread
sudo supervisorctl update all
sudo supervisorctl restart all
