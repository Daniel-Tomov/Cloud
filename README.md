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

