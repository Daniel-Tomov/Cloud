# configure.sh does not properly setup the services
Use the guide at the link in references
# HA Postgres
Run `configure.sh` on admin node to create configs for a HA Postgres. Setup the following before executing the script:
1. Change the variables at the top of the script
2. Ensure you have a SSH public key for the user on the systems.

The script will install patroni, ha-proxy, keepalived, PostgreSQL, and etcd on the three systems specified in the script. If you want more systems in the cluster, follow the guide in the references.

References:
https://technotim.live/posts/postgresql-high-availability/