#!/usr/bin/env sh

nginx -V
sudo yes | cp -f etc/nginx/sites-avalible/rosreestr /etc/nginx/sites-avalible/rosreestr
sudo ln -s /etc/nginx/sites-available/rosreestr /etc/nginx/sites-enabled/rosreestr
sudo /etc/init.d/nginx reload
