import psycopg2
from os import urandom
from datetime import timedelta, datetime
from utils import (
    hash_512,
    sanitize_input,
    current_time_str,
    current_time_dt,
    convert_time_dt_str,
    add_time_to_current_str
)
from threading import Thread
from time import sleep
from proxmox import power_off_vms_for_user


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
        connection, cursor = self.connect()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS last_login (username VARCHAR(16) UNIQUE, timestamp TIMESTAMP);"
        )
        
        connection.commit()
        connection.close()

    def add_last_login_to_db(self, username: str) -> str:
        username = sanitize_input(username)
        print(f'User {username} logged in. Adding them to the db.')
        Thread(target=self.async_add_last_login_to_db, kwargs={"username": username}).start()

    def async_add_last_login_to_db(self, username: str):
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
        while True:
            sleep(5) # 5 minutes
            connection, cursor = self.connect()
            cursor.execute(f"SELECT * FROM last_login WHERE timestamp < %s", (add_time_to_current_str(hours=-1 * self.system_config['proxmox_nodes']['shutdown_timeout']),))
            result = cursor.fetchall()
            if len(result) == 0:
                continue
            connection.close()

            for i in result:
                power_off_vms_for_user(i[0])
        

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
    
