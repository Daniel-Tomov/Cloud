# Proxmox Automatic Installation

## ISO Image
1. Download ISO from proxmox website.
2. Download the `proxmox-auto-install-assistant` binary
3. Install the `xorriso` binary (`proxmox-auto-install-assistant` requires it)
3. Run the command `proxmox-auto-install-assistant prepare-iso ~/path/to/iso.iso --fetch-from http`

4. In the firewall DHCP server, set DHCP option 250 to the URL of the webserver proxying traffic for the Proxmox webapp
5. Set DHCP option 251 to the sha256 fingerprint of the certificate (if using HTTPS). `openssl x509 -noout -fingerprint -sha256 -inform pem -in /path/to/certificate`. \*Note: There are two URLs in `answer.toml`. One is for the nginx server, the other is for the webapp.
6. Upload the prepared ISO image to the host Proxmox server.


## HTTP(S) server
The nginx configuration script does this automatically
1. Install `nginx`
2. Configure SSL `openssl req -x509 -newkey rsa:4096 -keyout <domain>.key.pem -out <domain>.cert.pem -sha256 -days 365 -nodes`
3. Upload configurations to `/etc/nginx/sites-available/`
4. Create symlinks of those configurations to `/etc/nginx/sites-enabled`
5. Check configuration and restart `sudo nginx -t && sudo service nginx restart`