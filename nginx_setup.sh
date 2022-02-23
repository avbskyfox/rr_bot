#!/usr/bin/env sh

nginx -V
yes | sudo cp -f etc/nginx/sites-avalible/rosreestr /etc/nginx/sites-availible/rosreestr
sudo ln -f -s /etc/nginx/sites-available/rosreestr /etc/nginx/sites-enabled/rosreestr
sudo /etc/init.d/nginx reload
