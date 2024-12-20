#!/bin/bash
echo "#" $(cat /etc/apt/sources.list.d/pve-enterprise.list ) > /etc/apt/sources.list.d/pve-enterprise.list # disable enterprise repository
echo "#" $(cat /etc/apt/sources.list.d/ceph.list ) > /etc/apt/sources.list.d/ceph.list # disable ceph repository
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-community.list # enable community repository

apt update
apt-get install qemu-guest-agent -y
systemctl start qemu-guest-agent
systemctl enable qemu-guest-agent


apt install curl net-tools -y # basic tools

# Add additional interfaces
cat <<EOF >> /etc/network/interfaces
        bridge-vlan-aware yes
        bridge-vids 2-4094
#Proxmox Access

auto vmbr1
iface vmbr1 inet manual
        bridge-ports ens19
        bridge-stp off
        bridge-fd 0
#OPNsense WAN

auto vmbr2
iface vmbr2 inet manual
        bridge-ports ens20
        bridge-stp off
        bridge-fd 0
#Internal Adapter. Put your VMs and containers here.
EOF


# Download recommended firewall
mkdir -p /var/lib/vz/template/iso
cd /var/lib/vz/template/iso
wget {{ firewall_img_domain }}/{{ FW_IMAGE }} --no-check-certificate #.bz2 # --no-check-certificate
#bunzip2 OPNsense-24.7-vga-amd64.img.bz2

curl -k -L {{ create_fw_url }} # TODO