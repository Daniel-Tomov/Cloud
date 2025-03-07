#!/bin/bash

apt install git curl openssl -y

mkdir /usr/src/ -p
cd /usr/src/
#wget https://github.com/Daniel-Tomov/Cloud/archive/refs/heads/main.zip -O cloud.zip
git clone https://github.com/Daniel-Tomov/Cloud
#unzip cloud.zip
#cd Cloud-main
cd Cloud
cd webapp

echo -e "US\nVirginia\nVirginia Beach\nDaniel Tomov\nLab\nlab.com\ntest@lab.com\n\n\n" | openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes

pip3 install -r requirements.txt
python3 main.py

