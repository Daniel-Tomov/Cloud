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
from utils import current_time_str, current_time_dt, convert_time_str_dt, hash_512
from db import (
    add_session_to_db,
    get_session_from_db,
    remove_session_from_db,
    update_session_in_db,
    does_user_exist_in_db,
    check_password_against_db,
    add_user_to_db,
    check_ip
)
banner = open("banner.txt", "r").read()

load_dotenv()
session_length = int(getenv("session_length"))  # minutes
pve_net = getenv("PVE_NET")  # minutes


class Auth:
    def __init__(self, app: Flask, proxmox_data_cache: dict):
        self.app = app
        self.proxmox_data_cache = proxmox_data_cache

        self.register_routes()
        
    def verify_user_can_access_ip(self, ip: str):
        if pve_net not in ip:
            return True
        username = get_session_from_db(session["id"])[0]
        
        if ip not in self.proxmox_data_cache:
            # need to check db
            print(f"ip {ip} not in vm ip cache, going to db")
            if check_ip(username, ip):
                self.proxmox_data_cache[ip] = ['dtomo001']
                return True
            self.proxmox_data_cache[ip] = []
            return False
        
        if username in self.proxmox_data_cache[ip]:
            return True # found ip in cache at username
        
        #print(f"{username} not in cache for {ip}")
        
        if check_ip(username, ip):
            self.proxmox_data_cache[ip].append('dtomo001')
            return True
        return False

    def register_routes(self):
        @self.app.route("/web/register", methods=["GET", "POST"])
        def register():
            if request.method == "GET":
                if "id" not in session or not check_session():
                    return make_response(
                        render_template("login.html", page="register", extra_content="", banner=banner)
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
                        banner=banner
                    )
                )
                r.set_cookie("session", "")
                return r

            password = request.form["password"]

            add_user_to_db(username=username, password=hash_512(password))
            #create_session(username=username)
            return redirect(url_for("login"))

        @self.app.route("/web/login", methods=["GET", "POST"])
        def login():
            if request.method == "GET":
                if "id" not in session or not check_session():
                    r = make_response(
                        render_template("login.html", page="login", extra_content="", banner=banner)
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
                        "login.html", page="login", extra_content="Incorrect", banner=banner
                    )
                )
            if not check_password_against_db(
                username=username, password=hash_512(password)
            ):
                r = make_response(
                    render_template(
                        "login.html", page="login", extra_content="Incorrect", banner=banner
                    )
                )
                r.set_cookie("session", "")
                return r
            create_session(username=username)

            return redirect(url_for("index"))

        @self.app.route("/web/update_session", methods=["GET"])
        def update_session_route():
            update_session_in_db(session['id'])
            return "done"

        @self.app.route("/web/logout")
        def logout():
            return invalidate_session()

        @self.app.route("/auth-proxy")
        def auth_proxy():
            failed = make_response("<h1>Access denied!</h1>", 401)
            failed.set_cookie("protocol", "")
            failed.set_cookie("ip", "")
            failed.set_cookie("port", "")
            
            if "id" not in session or not check_session():
                return failed
            
            ip = request.cookies.get("ip")
            port = request.cookies.get("port")
            protocol = request.cookies.get("protocol")
            
            if ip == None or port == None or protocol == None:
                return failed

            try:
                int(port)
            except:
                return failed

            if self.verify_user_can_access_ip(ip):
                return make_response("<h1>You aren't supposed to be here!</h1>", 200)
            else:
                print(f'{session} tried to access ip {ip}, but does not have access')
                return failed
                    
            return make_response("<h1>You aren't supposed to be here!</h1>", 200)


def compare_sessions(time_old: datetime, time_new: datetime) -> bool:
    return time_new - time_old < timedelta(minutes=session_length)


def check_session() -> bool:
    from_db = get_session_from_db(session["id"])
    if len(from_db) == 0:
        return False 
    return compare_sessions(from_db[2], current_time_dt())


def create_session(username: str):
    session["id"] = add_session_to_db(username=username)


def invalidate_session():
    if "id" in session:
        remove_session_from_db(session["id"])
    session.pop("id", None)
    r = make_response(redirect(url_for("login")))
    r.set_cookie("session", "")
    return r