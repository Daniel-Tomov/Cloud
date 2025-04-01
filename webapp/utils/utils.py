import hashlib
from datetime import datetime
import string

date_format = "%d %b %Y %H:%M:%S"


def hash_512(s: str) -> str:
    for _ in range(0, 2):
        s = hashlib.sha512(s.encode("utf-8")).hexdigest()
    return s


def sanitize_input(s: str, allowed_characters="") -> str:
    valid = string.ascii_uppercase + string.ascii_lowercase + "0123456789"
    new_s = ""
    for c in s:
        if c in valid or c in allowed_characters:
            new_s += c
    return new_s


### TIME
def current_time_str() -> str:
    return datetime.now().strftime(format=date_format)


def current_time_dt() -> datetime:
    return datetime.now()


def convert_time_str_dt(time: str) -> datetime:
    return datetime.strptime(time, date_format)

def convert_time_dt_str(time: datetime) -> str:
    return time.strftime(date_format)
