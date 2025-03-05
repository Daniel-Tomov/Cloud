#!/bin/bash

apt install git curl -y

mkdir /usr/src/ -p
cd /usr/src/
#wget https://github.com/Daniel-Tomov/Cloud/archive/refs/heads/main.zip -O cloud.zip
git clone https://github.com/Daniel-Tomov/Cloud
#unzip cloud.zip
#cd Cloud-main
cd Cloud
cd webapp

pip3 install -r requirements.txt
python3 main.py

