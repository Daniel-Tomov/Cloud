#!/bin/bash
sudo apt update
sudo apt install nginx

# Certificate stuff
country=""
state=""
city=""
organization=""
organizational_unit=""


webapp_domain=""
webapp=""
db_domain=""
db_webapp=""
proxmox_domain=""
proxmox_webapp=""
opnsense_iso_name="OPNsense-24.7-vga-amd64.img"


mkdir -p /etc/nginx/certs/


cat lab.conf | sed "s/_domain_/$webapp_domain/g" | sed "s/_webapp_ip_/$webapp/g" > /etc/nginx/sites-available/$webapp_domain.conf
ln -s /etc/nginx/sites-available/$webapp_domain.conf /etc/nginx/sites-enabled/
echo -e "$country\n$state\n$city\n$organization\n$organizational_unit\n$webapp_domain\n" | openssl req -x509 -newkey rsa:4096 -keyout /etc/nginx/certs/$webapp_domain.key.pem -out /etc/nginx/certs/$webapp_domain.com.cert.pem -sha256 -days 365 -nodes


cat db.conf | sed "s/_domain_/$db_domain/g" | sed "s/_webapp_ip_/$db_webapp/g" > /etc/nginx/sites-available/$db_domain.conf
ln -s /etc/nginx/sites-available/$db_domain.conf /etc/nginx/sites-enabled/
echo -e "$country\n$state\n$city\n$organization\n$organizational_unit\n$db_domain\n" | openssl req -x509 -newkey rsa:4096 -keyout /etc/nginx/certs/$db_domain.key.pem -out /etc/nginx/certs/$db_domain.cert.pem -sha256 -days 365 -nodes


cat proxmox.conf | sed "s/_domain_/$proxmox_domain/g" | sed "s/_webapp_ip_/$proxmox_webapp/g" | sed "s/_opnsense_iso_name_/$opnsense_iso_name/g" > /etc/nginx/sites-available/$proxmox_domain.conf
ln -s /etc/nginx/sites-available/$proxmox_domain.conf /etc/nginx/sites-enabled/
echo -e "$country\n$state\n$city\n$organization\n$organizational_unit\n$proxmox_domain\n" | openssl req -x509 -newkey rsa:4096 -keyout /etc/nginx/certs/$proxmox_domain.key.pem -out /etc/nginx/certs/$proxmox_domain.cert.pem -sha256 -days 365 -nodes

echo "This goes into .env in /proxmox and DHCP option 251. Put the full URL to answer.toml (Proxmox domain) in DHCP option 250."
openssl x509 -noout -fingerprint -sha256 -inform pem -in /etc/nginx/certs/$proxmox_domain.cert.pem