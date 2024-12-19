from flask import (
    Flask,
    session,
    make_response,
    render_template,
    request,
    url_for,
    redirect,
)
from datetime import datetime, timedelta
from os import urandom, getenv
from dotenv import load_dotenv
load_dotenv()
from utils import current_time_str, current_time_dt, convert_time_str_dt, hash_512
from db import (
    add_session_to_db,
    get_session_from_db,
    remove_session_from_db,
    update_session_in_db,
    does_user_exist_in_db,
    check_password_against_db,
    add_user_to_db,
)

session_length = int(getenv("session_length"))  # minutes


class Auth:
    def __init__(self, app: Flask):
        self.app = app

        self.register_routes()

    def register_routes(self):
        @self.app.route("/register", methods=["GET", "POST"])
        def register():
            if request.method == "GET":
                if "id" not in session or not check_session():
                    return make_response(
                        render_template("login.html", page="register", extra_content="")
                    )
                return redirect(url_for("index"))

            if "username" not in request.form and "password" not in request.form:
                return invalidate_session()

            username = request.form["username"]
            if does_user_exist_in_db(username=username):
                r = make_response(
                    render_template(
                        "login.html",
                        page="register",
                        extra_content="That username is taken",
                    )
                )
                r.set_cookie("session", "")
                return r

            password = request.form["password"]

            add_user_to_db(username=username, password=hash_512(password))
            #create_session(username=username)
            return redirect(url_for("login"))

        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "GET":
                if "id" not in session or not check_session():
                    r = make_response(
                        render_template("login.html", page="login", extra_content="")
                    )
                    r.set_cookie("session", "")
                    return r
                return redirect(url_for("index"))

            if "username" not in request.form and "password" not in request.form:
                return invalidate_session()

            username = request.form["username"]
            password = request.form["password"]

            if username == "" or password == "":
                return make_response(
                    render_template(
                        "login.html", page="login", extra_content="Incorrect"
                    )
                )
            if not check_password_against_db(
                username=username, password=hash_512(password)
            ):
                r = make_response(
                    render_template(
                        "login.html", page="login", extra_content="Incorrect"
                    )
                )
                r.set_cookie("session", "")
                return r
            create_session(username=username)

            return redirect(url_for("index"))

        @self.app.route("/update_session", methods=["GET"])
        def update_session_route():
            update_session_in_db()

        @self.app.route("/logout")
        def logout():
            return invalidate_session()

        @self.app.route("/auth-proxy")
        def auth_proxy():
            if "id" not in session or not check_session():
                return make_response("<h1>Access denied!</h1>", 401)
            return make_response("<h1>You aren't supposed to be here!</h1>", 200)


def compare_sessions(time_old: datetime, time_new: datetime) -> bool:
    return time_new - time_old < timedelta(minutes=session_length)


def check_session() -> bool:
    from_db = get_session_from_db()
    if len(from_db) == 0:
        return False
    return compare_sessions(convert_time_str_dt(from_db[2]), current_time_dt())


def create_session(username: str):
    session["id"] = add_session_to_db(username=username)


def invalidate_session():
    if "id" in session:
        remove_session_from_db()
    session.pop("id", None)
    r = make_response(redirect(url_for("login")))
    r.set_cookie("session", "")
    return r
