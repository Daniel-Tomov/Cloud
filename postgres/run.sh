#!/bin/bash

mkdir /usr/src/ -p
cd /usr/src/
wget https://github.com/Daniel-Tomov/Cloud/archive/refs/heads/main.zip -o cloud.zip

unzip cloud.zip
cd cloud
cd postgres

pip3 install -r requirements.txt
python3 main.py