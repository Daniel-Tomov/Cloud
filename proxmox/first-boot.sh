#!/bin/bash

# Change network config before using internet resources
cat <<EOF > /etc/network/interfaces
auto lo
iface lo inet loopback

iface ens18 inet manual

auto vmbr0
iface vmbr0 inet dhcp
        bridge-ports ens18
        bridge-stp off
        bridge-fd 0

iface ens19 inet manual
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

source /etc/network/interfaces.d/*
EOF

ifreload -a
dhclient -r vmbr0
dhclient vmbr0
dhclient -r vmbr0
dhclient vmbr0
dhclient -r vmbr0
dhclient vmbr0

sleep 5

echo "#" $(cat /etc/apt/sources.list.d/pve-enterprise.list ) > /etc/apt/sources.list.d/pve-enterprise.list # disable enterprise repository
echo "#" $(cat /etc/apt/sources.list.d/ceph.list ) > /etc/apt/sources.list.d/ceph.list # disable ceph repository
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-community.list # enable community repository

apt update
apt install curl net-tools -y # basic tools

mkdir -p /var/lib/vz/template/iso
cd /var/lib/vz/template/iso

#{{replace_with_vms}}

apt-get install qemu-guest-agent -y

# change ip in /ets/hosts
cp /etc/hosts /etc/hosts.backup

echo "#!/bin/bash" >> /etc/create_hosts_file.sh
echo "old_ip=\$(cat /etc/hosts.backup | head -n 2 | tail -n 1 | awk '{print \$1}')" >> /etc/create_hosts_file.sh
echo "new_ip=\$(ip a | grep 'vmbr0: ' -A 2 | tail -n 1 | awk '{print \$2}' | awk -F '/' '{print \$1}')" >> /etc/create_hosts_file.sh
echo 'cat /etc/hosts.backup | sed "s/$old_ip/$new_ip/g" > /etc/hosts' >> /etc/create_hosts_file.sh
echo 'dhclient vmbr0; dhclient -r vmbr0; dhclient vmbr0" > /etc/hosts' >> /etc/create_hosts_file.sh

cat <<EOF > /etc/systemd/system/hosts_file.service
[Unit]
Description=Recreate Hosts File after DHCP
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/etc/create_hosts_file.sh
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable hosts_file
systemctl start hosts_file

systemctl start qemu-guest-agent
systemctl enable qemu-guest-agent