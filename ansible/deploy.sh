#!/usr/bin/env sh

ansible-playbook -i inventory.yml deploy.yml -vvv
