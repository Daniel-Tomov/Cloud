from datetime import datetime

date_format = "%Y-%m-%d %H:%M:%S"

### TIME
def current_time_str() -> str:
    return datetime.now().strftime(format=date_format)


def current_time_dt() -> datetime:
    return datetime.now()


def convert_time_str_dt(time: str) -> datetime:
    return datetime.strptime(time, date_format)

def convert_time_dt_str(time: datetime) -> str:
    return time.strftime(date_format)
