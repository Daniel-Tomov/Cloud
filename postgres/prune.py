import psycopg2
from datetime import timedelta, datetime
from utils import (
    current_time_str,
    current_time_dt,
    convert_time_dt_str,
)
from threading import Thread
from time import sleep
from yaml import safe_load

class Prune:
    def __init__(self, system_config):
        self.data = system_config['cache_database']
        self.database=self.data['database']
        self.user=self.data['user']
        self.password=self.data['password']
        self.host=self.data['host']
        self.port=self.data['port']
        self.sslmode=self.data['sslmode']
        # {"id": {"id": "", "username": "", "last_accessed": datetime}}
        self.sessions_cache = {}

        self.session_length = int(system_config['session_length'])  # minutes


        Thread(target=self.async_session_prune).start()
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
    
    def session_prune(self):
        connection, cursor = self.connect()
        expiration_time = current_time_dt() - timedelta(minutes=self.session_length)                
        expiration_time = convert_time_dt_str(expiration_time)
        query = f"DELETE FROM sessions WHERE last_accessed < '{expiration_time}';"
        print(query)
        cursor.execute(query)
        connection.commit()


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

    with open('../../vm-options.yaml', 'r') as config:
        system_config = safe_load(config)
    Prune(system_config=system_config)
    """"""
else:
    """"""
