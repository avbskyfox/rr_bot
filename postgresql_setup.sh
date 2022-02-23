#!/usr/bin/env sh

sudo -u postgres psql -v ON_ERROR_STOP=1 -P pager=off << EOF
    create user web with password 'gqqw14d6DY';
    alter role web set client_encoding to 'utf8';
    alter role web set default_transaction_isolation to 'read committed';
    alter role web set timezone to 'Europe/Moscow';
    create database rosreestr_db owner web;
EOF
