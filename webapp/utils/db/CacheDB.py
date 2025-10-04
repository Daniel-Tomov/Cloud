import psycopg2
from os import urandom
from datetime import timedelta, datetime
from utils.utils import (
    hash_512,
    sanitize_input,
    current_time_str,
    current_time_dt,
    convert_time_dt_str,
)
from threading import Thread
from time import sleep





class CacheDB:
    def __init__(self, args):
        self.data = args.system_config['cache_database']
        self.database=self.data['database']
        self.user=self.data['user']
        self.password=self.data['password']
        self.host=self.data['host']
        self.port=self.data['port']
        self.sslmode=self.data['sslmode']
        # {"id": {"id": "", "username": "", "last_accessed": datetime, "auth_type": str}}
        self.sessions_cache = {}

        self.session_length = int(args.system_config['session_length'])  # minutes

        self.create_tables()

        #Thread(target=self.async_session_prune).start()

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
            "CREATE TABLE IF NOT EXISTS sessions (username VARCHAR(16), id VARCHAR(32), last_accessed TIMESTAMP, auth_type VARCHAR(16));"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS vm_ips (ip VARCHAR(16) UNIQUE, usernames VARCHAR(65535));"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS vm_requests (username VARCHAR(65535), description VARCHAR(65535));"
        )
        
        connection.commit()
        connection.close()

    def add_session_to_db(self, username: str, auth_type: str) -> str:
        username = sanitize_input(username)
        
        id = urandom(16).hex()
        self.sessions_cache[id] = {"id": id, "username": username, "last_accessed": current_time_dt(), "auth_type": auth_type}

        Thread(target=self.async_add_session_to_db, kwargs={"username": username, "id": id, "auth_type": auth_type}).start()
        
        return id

    def async_add_session_to_db(self, username: str, id: str, auth_type: str):
        connection, cursor = self.connect()
        cursor.execute(
            f"INSERT INTO sessions (username, id, last_accessed, auth_type) VALUES (%s, %s, %s, %s)",
            (username, id, current_time_str(), auth_type)
        )
        connection.commit()
        connection.close()
        # cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")
        

    def get_session_from_db(self, id: str) -> list:
        #print(self.sessions_cache)
        if id in self.sessions_cache and "username" in self.sessions_cache[id]:
            #print(f'found {id} in cache')
            return [self.sessions_cache[id]["username"], self.sessions_cache[id]["id"], self.sessions_cache[id]["last_accessed"], self.sessions_cache[id]["auth_type"]]
        #else:
            #print(f'Session {id} not found in cache, going to db')
        connection, cursor = self.connect()
        cursor.execute(f"SELECT * FROM sessions WHERE id = %s", (id,))
        result = cursor.fetchall()
        #print(result)
        if len(result) == 0:
            return []
        result = result[0]
        self.sessions_cache[id] = {"id": result[1], "username": result[0], "last_accessed": result[2], "auth_type": result[3]}
        connection.close()
        return result


    def update_session_in_db(self, id: str):
        if id in self.sessions_cache and "last_accessed" in self.sessions_cache[id]:
            self.sessions_cache[id]["last_accessed"] = current_time_dt()
        #print("creating update session thread")
        Thread(target=self.async_update_session_in_db, kwargs={"id": id}).start()
        #print("after update session thread")

    def async_update_session_in_db(self, id: str):
        connection, cursor = self.connect()
        cursor.execute(
            f"UPDATE sessions SET last_accessed = %s WHERE id = %s", (current_time_str(), id)
        )
        connection.commit()
        #print("updated session")
        connection.close()


    def remove_session_from_db(self, id: str):
        if id in self.sessions_cache:
            del self.sessions_cache[id]
        Thread(target=self.async_remove_session_from_db, kwargs={"id": id}).start()
        

    def async_remove_session_from_db(self, id: str):
        connection, cursor = self.connect()
        cursor.execute(f"DELETE FROM sessions WHERE id = %s", (id,))
        connection.commit()
        connection.close()

    def check_ip(self, username: str, ip: str) -> bool:
        connection, cursor = self.connect()
        cursor.execute(f"SELECT * FROM vm_ips WHERE ip = %s", (ip,))
        result = cursor.fetchall()
        #print(result)
        if len(result) == 0:
            return False
        #print(f"found {result} result in db for vm ip cache for ip {ip}")
        result = result[0]
        connection.close()
        return username in result[1]


    def set_vm_ip_map(self, ip: str, usernames: str):
        Thread(target=self.async_set_vm_ip_map, kwargs={"ip": ip, "usernames": usernames}).start()
        

    def async_set_vm_ip_map(self, ip: str, usernames: str):
        connection, cursor = self.connect()
        cursor.execute(f"""
            INSERT INTO vm_ips (ip, usernames) 
            VALUES (%s, %s) 
            ON CONFLICT (ip) 
            DO UPDATE SET usernames = EXCLUDED.usernames
        """, (ip, usernames))

        connection.commit()
        connection.close()

    def add_request_to_db(self, username: str, description: str) -> str:
        username = sanitize_input(username)
        description = sanitize_input(description, ",. ")
        Thread(target=self.async_add_request_to_db, kwargs={"username": username, "description": description}).start()
        

    def async_add_request_to_db(self, username: str, description: str):
        connection, cursor = self.connect()
        cursor.execute(
            f"INSERT INTO vm_requests (username, description) VALUES (%s, %s)",
            (username, description)
        )
        connection.commit()
        # cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")
        connection.close()


    def session_prune(self):
        expiration_time = current_time_dt() - timedelta(minutes=self.session_length)
        for id in self.sessions_cache:
            if "last_accessed" in self.sessions_cache[id]:
                if self.sessions_cache[id]['last_accessed'] < expiration_time:
                    self.sessions_cache[id] = {}


    def async_session_prune(self):
        global status
        while True:
            status = self.session_prune()
            sleep(
                (self.session_length / 2) * 60
            )  # remove expired sessions every session_length / 2 minutes


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
    
