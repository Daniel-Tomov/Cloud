#!/bin/bash

mkdir /usr/src/ -p
cd /usr/src/
wget https://github.com/Daniel-Tomov/Cloud/archive/refs/heads/main.zip -O cloud.zip

unzip cloud.zip
cd Cloud-main
cd proxmox

pip3 install -r requirements.txt
python3 main.py