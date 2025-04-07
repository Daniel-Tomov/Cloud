#!/bin/bash
echo "#" $(cat /etc/apt/sources.list.d/pve-enterprise.list ) > /etc/apt/sources.list.d/pve-enterprise.list # disable enterprise repository
echo "#" $(cat /etc/apt/sources.list.d/ceph.list ) > /etc/apt/sources.list.d/ceph.list # disable ceph repository
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-community.list # enable community repository

apt update
apt install curl net-tools -y # basic tools

# Add additional interfaces
cat <<EOF >> /etc/network/interfaces


auto vmbr1
iface vmbr1 inet manual
        bridge-ports ens19
        bridge-stp off
        bridge-fd 0
#OPNsense WAN

auto vmbr2
iface vmbr2 inet manual
	bridge-ports none
	bridge-stp off
	bridge-fd 0
	bridge-vlan-aware yes
	bridge-vids 2-4094
#Internal Adapter. Put your VMs and containers here.
EOF
ifreload -a

# Download recommended firewall
mkdir -p /var/lib/vz/template/iso
cd /var/lib/vz/template/iso
#{{replace_with_vms}}

apt-get install qemu-guest-agent -y
systemctl start qemu-guest-agent
systemctl enable qemu-guest-agent