import psycopg2
from os import getenv, urandom
from dotenv import load_dotenv
from datetime import timedelta
from utils import (
    hash_512,
    sanitize_input,
    current_time_str,
    current_time_dt,
    convert_time_dt_str,
)
from threading import Thread
from time import sleep

load_dotenv()
POSTGRES_DB = getenv("POSTGRES_DB")
POSTGRES_USER = getenv("POSTGRES_USER")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = getenv("POSTGRES_HOST")
session_length = int(getenv("session_length"))  # minutes

connection = psycopg2.connect(
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=5432,
)
cursor = connection.cursor()


def create_tables():
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (username VARCHAR(16), password VARCHAR(128), salt VARCHAR(32));"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS sessions (username VARCHAR(16), id VARCHAR(32), last_accessed TIMESTAMP);"
    )
    connection.commit()


def check_password_against_db(username: str, password: str) -> bool:
    username = sanitize_input(username)
    cursor.execute(f"SELECT salt FROM users WHERE username = '{username}';")
    salt = cursor.fetchall()
    if len(salt) == 0:  # username not in database
        return False
    salt = salt[0][0]
    password = hash_512(password + salt)
    cursor.execute(
        f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}';"
    )
    result = cursor.fetchall()
    return len(result) == 1


def does_user_exist_in_db(username: str) -> bool:
    username = sanitize_input(username)
    cursor.execute(f"SELECT username FROM users WHERE username = '{username}';")
    result = cursor.fetchall()
    return len(result) == 1  # returns true if the user exists


def add_user_to_db(username: str, password: str):
    username = sanitize_input(username)
    salt = urandom(16).hex()
    password = hash_512(password + salt)
    cursor.execute(
        f"INSERT INTO users (username, password, salt) VALUES ('{username}', '{password}', '{salt}');"
    )
    connection.commit()


def add_session_to_db(username: str) -> str:
    username = sanitize_input(username)
    id = urandom(16).hex()
    cursor.execute(
        f"INSERT INTO sessions (username, id, last_accessed) VALUES ('{username}', '{id}', '{current_time_str()}');"
    )
    connection.commit()
    result = cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")
    return id


def get_session_from_db(id) -> list:
    cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")
    result = cursor.fetchall()
    if len(result) == 0:
        return []
    return result[0]


def update_session_in_db(id: str):
    cursor.execute(
        f"UPDATE sessions SET last_accessed = '{current_time_str()}' WHERE id = '{id}';"
    )


def remove_session_from_db(id):
    cursor.execute(f"DELETE FROM sessions WHERE id = '{id}';")
    connection.commit()


create_tables()


def session_prune():
    expiration_time = current_time_dt() - timedelta(minutes=session_length)
    expiration_time = convert_time_dt_str(expiration_time)
    cursor.execute(f"DELETE FROM sessions WHERE last_accessed < '{expiration_time}';")
    connection.commit()


def async_session_prune():
    global status
    while True:
        status = session_prune()
        sleep(
            (session_length / 2) * 60
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
    Thread(target=async_session_prune).start()
