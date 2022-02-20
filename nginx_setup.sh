#!/usr/bin/env sh

nginx -V
yes | cp -f etc/nginx/sites-avalible/rosreestr /etc/nginx/sites-avalible/rosreestr
ln -s /etc/nginx/sites-available/rosreestr /etc/nginx/sites-enabled/rosreestr
/etc/init.d/nginx reload
