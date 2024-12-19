from dotenv import load_dotenv
import hashlib
from datetime import datetime

load_dotenv()
date_format = "%a, %d %b %Y %H:%M:%S %Z"


def hash_512(s: str) -> str:
    for _ in range(0, 2):
        s = hashlib.sha512(s.encode("utf-8")).hexdigest()
    return s


def sanitize_input(s: str) -> str:
    invalid = "`~!@#$%^&*()_-+=[{]}\\|;:'\",<.>/?"
    for c in invalid:
        s = s.replace(c, "")
    return s


### TIME
def current_time_str() -> str:
    return datetime.now().strftime(format=date_format)


def current_time_dt() -> datetime:
    return datetime.now()


def convert_time_str_dt(time: str) -> datetime:
    return datetime.strptime(time, date_format)

def convert_time_dt_str(time: datetime) -> str:
    return time.strftime(date_format)
