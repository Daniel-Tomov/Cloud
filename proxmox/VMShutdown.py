import psycopg2
from utils import (
    hash_512,
    sanitize_input,
    current_time_str,
    current_time_dt,
    convert_time_dt_str,
    add_time_to_current_str,
    compare_datetime_now
)
from threading import Thread
from time import sleep
from proxmox import set_vm_power, get_status


class VMShutdown:
    def __init__(self, system_config: dict):
        self.system_config = system_config
        self.database=self.system_config['cache_database']['database']
        self.user=self.system_config['cache_database']['user']
        self.password=self.system_config['cache_database']['password']
        self.host=self.system_config['cache_database']['host']
        self.port=self.system_config['cache_database']['port']
        self.sslmode=self.system_config['cache_database']['sslmode']
        
        self.create_tables()

        if self.system_config['proxmox_nodes']['shutdown_timeout'] != 0:
            Thread(target=self.async_vm_shutdown).start()

    def connect(self):
        connection = psycopg2.connect(
            database=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            sslmode=self.sslmode
        )
        return connection, connection.cursor()

    def create_tables(self):
        if self.host == "":
            return
        connection, cursor = self.connect()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS last_login (username VARCHAR(16) UNIQUE, timestamp TIMESTAMP);"
        )
        
        connection.commit()
        connection.close()

    def add_last_login_to_db(self, username: str):
        username = sanitize_input(username)
        #print(f'User {username} logged in. Adding them to the db.')
        Thread(target=self.async_add_last_login_to_db, kwargs={"username": username}).start()

    def async_add_last_login_to_db(self, username: str):
        if self.host == "":
            return
        connection, cursor = self.connect()
        cursor.execute(f"""
            INSERT INTO last_login (username, timestamp) 
            VALUES (%s, %s) 
            ON CONFLICT (username) 
            DO UPDATE SET timestamp = EXCLUDED.timestamp
        """, (username, current_time_str()))
        connection.commit()
        connection.close()
        # cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")

    def async_vm_shutdown(self):
        if self.host == "":
            return
        while True:
            connection, cursor = self.connect()

            # Get cutoff time
            cutoff_time = add_time_to_current_str(
                hours=-1 * self.system_config['proxmox_nodes']['shutdown_timeout']
            )

            # Query only what we need: username + last login
            cursor.execute("SELECT username, timestamp FROM last_login WHERE timestamp < %s", (cutoff_time,))
            rows = cursor.fetchall()
            connection.commit()
            connection.close()

            # Build dict for quick lookup: {username: last_login_time}
            last_logins = {row[0]: row[1] for row in rows}

            vms_powered_on_too_long = []
            for entry in get_status():
                if (
                    "id" in entry and
                    "name" in entry and
                    entry['status'] == 'running' and
                    int(entry['id'].split('/')[1]) >= self.system_config['proxmox_nodes']['minimum_vmid'] and
                    entry["name"].rsplit("-")[1] not in self.system_config['proxmox_nodes']['exlude_nodes_from_shutdown_endwith']
                ):
                    uptime_hours = entry['uptime'] / 3600
                    timeout = self.system_config['proxmox_nodes']['shutdown_timeout']

                    if uptime_hours > timeout + 1:
                        cmd = "stop"
                    elif uptime_hours > timeout:
                        cmd = "shutdown"
                    else:
                        continue

                    vms_powered_on_too_long.append({
                        "name": entry['name'],
                        "node": entry['node'],
                        "vmid": entry['id'],
                        "command": cmd,
                    })

            print(f'{vms_powered_on_too_long=}')

            for vm in vms_powered_on_too_long:
                username = vm['name'].rsplit('-')[0]

                if username in last_logins:
                    # Compare time difference
                    delta_hours = compare_datetime_now(last_logins[username]).total_seconds() / 3600
                    if delta_hours <= self.system_config['proxmox_nodes']['shutdown_timeout'] + self.system_config['proxmox_nodes']['stop_timeout']:
                        vm['command'] = "shutdown"

                    set_vm_power(vm['node'], vm['vmid'], vm['command'])
                    print(f"Sending command {vm['command']} to {vm['name']} (ID {vm['vmid']}) on node {vm['node']}")


            sleep(600)  # Increase sleep to reduce DB load



if __name__ == "__main__":
    # cursor.execute("DROP TABLE sessions;")
    # connection.commit()
    # create_tables()
    # r = cursor.fetchall()
    # print(r)
    # async_session_prune()
    """"""
else:
    """"""
    
