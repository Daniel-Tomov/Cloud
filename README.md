# Cloud
Turn your Proxmox cluster into a cloud service for others to use. The service creates a Proxmox VM for each user.

## Installation
1. Create an nginx container/VM and run the `run.sh` script. This will give a fingerprint at the end.
2. Take that fingerprint and put it in DHCP option 251. In DHCP option 250, put the location of the https://proxmox_webapp_url/answer.toml there.
3. Configure the environment for Docker or k3s
4. Install PostgreSQL. Docker Compose config is provided, but normal install is prefered.
5. Run the webapp service (Docker or k3s)
6. Run the Proxmox webapp service (Docker or k3s)
7. Make sure it works

## Prepare LXC containers for K3S
0. Do all the things in the references below (ip forwarding, disable swap, etc)
1. Unpriviledged conainer
2. 
```
lxc.apparmor.profile: unconfined
lxc.cgroup2.devices.allow: a
lxc.cap.drop:
lxc.mount.auto: "proc:rw sys:rw"
```
3. in /etc/rc.local
```
#!/bin/sh -e
if [ ! -e /dev/kmsg ]; then
ln -s /dev/console /dev/kmsg
fi
mount --make-rshared /
```
```bash
chmod +x /etc/rc.local
/etc/rc.local
```
4. Install k3s on manager
`curl -sfL https://get.k3s.io | sh -s - server --disable traefik --write-kubeconfig-mode 644`
5. Config file is at /etc/rancher/k3s/k3s.yaml. Export it to admin machine to use it there. Will need to change IP in config file
6. Install k3s on workers. Change IP and token as appropriate. Token is at `/var/lib/rancher/k3s/server/node-token` on master.
```bash
apt update ; apt install curl tmux net-tools -y ; curl -sfL https://get.k3s.io | sh -s - agent --server https://ip:6443 --token 
```


References:
https://kevingoos.medium.com/kubernetes-inside-proxmox-lxc-cce5c9927942
https://kevingoos.medium.com/installing-k3s-in-an-lxc-container-2fc24b655b93