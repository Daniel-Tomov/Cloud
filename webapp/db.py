import psycopg2
from os import getenv, urandom
from dotenv import load_dotenv
from datetime import timedelta, datetime
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
POSTGRES_PORT = int(getenv("POSTGRES_PORT"))
session_length = int(getenv("session_length"))  # minutes

connection = psycopg2.connect(
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
)
cursor = connection.cursor()

# {"id": {"id": "", "username": "", "last_accessed": datetime}}
sessions_cache = {}

def create_tables():
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (username VARCHAR(16) UNIQUE, password VARCHAR(128), salt VARCHAR(32), admin boolean default false);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS sessions (username VARCHAR(16), id VARCHAR(32), last_accessed TIMESTAMP);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS vm_ips (ip VARCHAR(16) UNIQUE, usernames VARCHAR(65535));"
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
    Thread(target=async_add_user_to_db, kwargs={"username": username, "password": password}).start()

def async_add_user_to_db(username: str, password: str):
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
    sessions_cache[id] = {"id": id, "username": username, "last_accessed": current_time_dt()}

    Thread(target=async_add_session_to_db, kwargs={"username": username, "id": id}).start()
    
    return id

def async_add_session_to_db(username: str, id: str):
    cursor.execute(
        f"INSERT INTO sessions (username, id, last_accessed) VALUES ('{username}', '{id}', '{current_time_str()}');"
    )
    connection.commit()
    # cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")
    

def get_session_from_db(id: str) -> list:
    if id in sessions_cache and "username" in sessions_cache[id]:
        #print(f'found {id} in cache')
        return [sessions_cache[id]["username"], sessions_cache[id]["id"], sessions_cache[id]["last_accessed"]]
    #else:
        #print(f'Session {id} not found in cache, going to db')
    cursor.execute(f"SELECT * FROM sessions WHERE id = '{id}';")
    result = cursor.fetchall()
    #print(result)
    if len(result) == 0:
        return []
    result = result[0]
    sessions_cache[id] = {"id": result[1], "username": result[0], "last_accessed": result[2]}
    return result


def update_session_in_db(id: str):
    if id in sessions_cache and "last_accessed" in sessions_cache[id]:
        sessions_cache[id]["last_accessed"] = current_time_dt()
    #print("creating update session thread")
    Thread(target=async_update_session_in_db, kwargs={"id": id}).start()
    #print("after update session thread")

def async_update_session_in_db(id: str):
    cursor.execute(
        f"UPDATE sessions SET last_accessed = '{current_time_str()}' WHERE id = '{id}';"
    )
    connection.commit()
    #print("updated session")


def remove_session_from_db(id: str):
    if id in sessions_cache:
        del sessions_cache[id]
    Thread(target=async_remove_session_from_db, kwargs={"id": id}).start()
    

def async_remove_session_from_db(id: str):
    cursor.execute(f"DELETE FROM sessions WHERE id = '{id}';")
    connection.commit()

def check_ip(username: str, ip: str) -> bool:
    cursor.execute(f"SELECT * FROM vm_ips WHERE ip = '{ip}';")
    result = cursor.fetchall()
    #print(result)
    if len(result) == 0:
        return False
    #print(f"found {result} result in db for vm ip cache for ip {ip}")
    result = result[0]
    return username in result[1]


def set_vm_ip_map(ip: str, usernames: str):
    Thread(target=async_set_vm_ip_map, kwargs={"ip": ip, "usernames": usernames}).start()
    

def async_set_vm_ip_map(ip: str, usernames: str):
    cursor.execute(f"""
        INSERT INTO vm_ips (ip, usernames) 
        VALUES ('{ip}', '{usernames}') 
        ON CONFLICT (ip) 
        DO UPDATE SET usernames = EXCLUDED.usernames;
    """)

    connection.commit()

create_tables()


def session_prune():
    expiration_time = current_time_dt() - timedelta(minutes=session_length)
    for id in sessions_cache:
        if "last_accessed" in sessions_cache[id]:
            if sessions_cache[id]['last_accessed'] < expiration_time:
                sessions_cache[id] = {}


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
