import psycopg2
from dotenv import load_dotenv
from datetime import timedelta, datetime
from utils import (
    current_time_str,
    current_time_dt,
    convert_time_dt_str,
)
from threading import Thread
from time import sleep
from os import getenv

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



def session_prune():
    expiration_time = current_time_dt() - timedelta(minutes=session_length)                
    expiration_time = convert_time_dt_str(expiration_time)
    query = f"DELETE FROM sessions WHERE last_accessed < '{expiration_time}';"
    print(query)
    cursor.execute(query)
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
    Thread(target=async_session_prune).start()
    """"""
else:
    """"""
