# HA k3s on LXC containers
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
4. Install k3s on manager(s)
`curl -sfL https://get.k3s.io | sh -s - server --cluster-init --disable traefik --node-taint CriticalAddonsOnly=true:NoExecute --tls-san <ip> --tls-san <load balancer ip>`
 - Token is at `/var/lib/rancher/k3s/server/node-token`
 - `curl -sfL https://get.k3s.io | K3S_TOKEN=<token> sh -s - server --server https://<ip>:6443 --cluster-init --disable traefik --node-taint CriticalAddonsOnly=true:NoExecute --tls-san ip`
5. Config file is at /etc/rancher/k3s/k3s.yaml. Export it to admin machine to use it there. Will need to change IP in config file
6. Install k3s on workers. Change IP and token as appropriate. Token is at `/var/lib/rancher/k3s/server/node-token` on master.
```bash
curl -sfL https://get.k3s.io | K3S_TOKEN=SECRET sh -s - agent --server https://<ip or hostname of server>:6443 
```


References:
https://kevingoos.medium.com/kubernetes-inside-proxmox-lxc-cce5c9927942
https://kevingoos.medium.com/installing-k3s-in-an-lxc-container-2fc24b655b93
https://technotim.live/posts/k3s-ha-install/
https://docs.k3s.io/datastore/ha-embedded