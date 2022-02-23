#!/usr/bin/env sh

yes | sudo cp -f etc/supervisor/conf.d/asgi_prod.conf /etc/supervisor/conf.d/asgi_prod.conf
yes | sudo cp -f etc/supervisor/conf.d/rrtelebot_prod.conf /etc/supervisor/conf.d/rrtelebot_prod.conf

sudo supervisorctl reread
sudo supervisorctl restart all
