from requests import get
from dotenv import load_dotenv
from os import getenv
from flask import session
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

load_dotenv()
POSTGRES_WEBAPP_HOST = getenv("POSTGRES_WEBAPP_HOST")
POSTGRES_WEBAPP_verify_ssl = getenv("PROXMOX_WEBAPP_verify_ssl", "False") == "True"
if not POSTGRES_WEBAPP_verify_ssl:
    disable_warnings(InsecureRequestWarning)


def check_password_against_db(username: str, password: str) -> bool:
    return get(
        url=f"{POSTGRES_WEBAPP_HOST}/check_password_against_db/{username}/{password}", verify=POSTGRES_WEBAPP_verify_ssl
    ).json()["result"]


def does_user_exist_in_db(username: str) -> bool:
    return get(
        url=f"{POSTGRES_WEBAPP_HOST}/does_user_exist_in_db/{username}", verify=POSTGRES_WEBAPP_verify_ssl
    ).json()["result"]


def add_user_to_db(username: str, password: str):
    get(url=f"{POSTGRES_WEBAPP_HOST}/add_user_to_db/{username}/{password}", verify=POSTGRES_WEBAPP_verify_ssl)


def add_session_to_db(username: str) -> str:
    return get(
        url=f"{POSTGRES_WEBAPP_HOST}/add_session_to_db/{username}", verify=POSTGRES_WEBAPP_verify_ssl
    ).json()["result"]


def get_session_from_db() -> list:
    return get(
        url=f"{POSTGRES_WEBAPP_HOST}/get_session_from_db/{session["id"]}", verify=POSTGRES_WEBAPP_verify_ssl
    ).json()["result"]


def update_session_in_db():
    get(url=f"{POSTGRES_WEBAPP_HOST}/update_session_in_db/{session["id"]}", verify=POSTGRES_WEBAPP_verify_ssl)


def remove_session_from_db():
    get(url=f'{POSTGRES_WEBAPP_HOST}/remove_session_from_db/{session["id"]}', verify=POSTGRES_WEBAPP_verify_ssl)
