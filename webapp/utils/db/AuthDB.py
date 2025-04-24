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

class AuthDB:
    def __init__(self, data: dict):
        self.database=data['database']
        self.user=data['user']
        self.password=data['password']
        self.host=data['host']
        self.port=data['port']
        self.sslmode=data['sslmode']
        self.type=data['type']
        self.realm=data['realm']

        self.create_tables()

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

    def create_tables(self, ):
        connection, cursor = self.connect()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (username VARCHAR(16) UNIQUE, password VARCHAR(128), salt VARCHAR(32), admin boolean default false);"
        )
        connection.commit()
        connection.close()

    def authenticate_user(self, username: str, password: str) -> bool:
        connection, cursor = self.connect()
        username = sanitize_input(username)
        cursor.execute("SELECT salt FROM users WHERE username = %s", (username,))
        salt = cursor.fetchall()
        if len(salt) == 0:  # username not in database
            return False
        salt = salt[0][0]
        password = hash_512(hash_512(password) + salt)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        result = cursor.fetchall()
        connection.close()
        return len(result) == 1


    def does_user_exist_in_db(self, username: str) -> bool:
        username = sanitize_input(username)
        connection, cursor = self.connect()
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        result = cursor.fetchall()
        connection.close()
        return len(result) == 1  # returns true if the user exists


    def add_user_to_db(self, username: str, password: str):
        Thread(target=self.async_add_user_to_db, kwargs={"username": username, "password": password}).start()
        
    def async_add_user_to_db(self, username: str, password: str):
        connection, cursor = self.connect()
        username = sanitize_input(username)
        salt = urandom(16).hex()
        password = hash_512(hash_512(password) + salt)
        cursor.execute(
            f"INSERT INTO users (username, password, salt) VALUES (%s, %s, %s)",
            (username, password, salt)
        )
        connection.commit()
        connection.close()





if __name__ == "__main__":
    # connection.commit()
    # create_tables()
    """"""
else:
    """"""