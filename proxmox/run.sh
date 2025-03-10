#!/bin/bash

apt install git curl openssl -y

mkdir /usr/src/ -p
cd /usr/src/
#wget https://github.com/Daniel-Tomov/Cloud/archive/refs/heads/main.zip -O cloud.zip
git clone https://github.com/Daniel-Tomov/Cloud
#unzip cloud.zip
#cd Cloud-main
cd Cloud
cd proxmox

echo -e "\n\n\n\n\n\n" | openssl req -x509 -newkey rsa:4096 -keyout /usr/src/Cloud/proxmox/key.pem -out /usr/src/Cloud/proxmox/cert.pem -sha256 -days 365 -nodes

pip3 install -r requirements.txt
#python3 main.py
gunicorn --certfile=cert.pem --keyfile=key.pem --bind 0.0.0.0:5556 -w 1 main:http
