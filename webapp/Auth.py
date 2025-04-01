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
from utils.utils import current_time_dt
banner = open("static/text/banner.txt", "r").read()
from utils.db.AuthDB import AuthDB


class Auth:
    def __init__(self, args):
        self.app = args.app
        self.proxmox_data_cache = args.proxmox_data_cache
        self.system_config = args.system_config
        self.cache_db = args.cache_db

        self.auth_methods=args.auth_methods

        self.session_length = int(self.system_config['session_length'])  # minutes
        self.pve_net = self.system_config['proxmox_webapp']['pve_net']

        self.SERVICES = self.system_config['services']

        self.register_routes()
        
    def verify_user_can_access_ip(self, ip: str):
        if self.pve_net not in ip:
            return True
        username = self.cache_db.get_session_from_db(session["id"])[0]
        
        if ip not in self.proxmox_data_cache:
            # need to check db
            print(f"ip {ip} not in vm ip cache, going to db")
            if self.cache_db.check_ip(username, ip):
                self.proxmox_data_cache[ip] = ['dtomo001']
                return True
            self.proxmox_data_cache[ip] = []
            return False
        
        if username in self.proxmox_data_cache[ip]:
            return True # found ip in cache at username
        
        #print(f"{username} not in cache for {ip}")
        
        if self.cache_db.check_ip(username, ip):
            self.proxmox_data_cache[ip].append('dtomo001')
            return True
        return False
    
    def return_login_page(self, page="login", extra_content=""):
        return make_response(
            render_template("login.html", page=page, extra_content=extra_content, banner=banner, services=self.SERVICES)
        )
    
    def register_routes(self):
        @self.app.route("/web/register", methods=["GET", "POST"])
        def register():
            if request.method == "GET":
                if "id" not in session or not self.check_session():
                    return self.return_login_page(page="register")
                return redirect(url_for("index"))

            if "username" not in request.form and "password" not in request.form:
                return self.invalidate_session()

            username = request.form["username"]
            for auth_method in self.auth_methods:
                if not isinstance(auth_method, AuthDB):
                    continue
                if auth_method.does_user_exist_in_db(username=username):
                    r = self.return_login_page(page="register", extra_content="That username is taken")
                    r.set_cookie("session", "")
                    return r

                password = request.form["password"]

                auth_method.add_user_to_db(username=username, password=password)
                #create_session(username=username)
                return redirect(url_for("login"))
        
            return redirect(url_for("login"))

        @self.app.route("/web/login", methods=["GET", "POST"])
        def login():
            if request.method == "GET":
                if "id" not in session or not self.check_session():
                    r = self.return_login_page(page="login")
                    r.set_cookie("session", "")
                    return r
                return redirect(url_for("index"))

            if "username" not in request.form and "password" not in request.form:
                return self.invalidate_session()

            username = request.form["username"]
            password = request.form["password"]

            if username == "" or password == "":
                return self.return_login_page(page="login", extra_content="Incorrect username or password")
            for auth_method in self.auth_methods:
                if auth_method.authenticate_user(username=username, password=password):
                    print(f"authenticated {username} with {auth_method.type}")
                    self.create_session(username=username)
                    return redirect(url_for("index"))

            r = self.return_login_page(page="login", extra_content="Incorrect username or password")
            r.set_cookie("session", "")
            return r

        @self.app.route("/web/update_session", methods=["GET"])
        def update_session_route():
            self.cache_db.update_session_in_db(session['id'])
            return "done"

        @self.app.route("/web/logout")
        def logout():
            return self.invalidate_session()

        @self.app.route("/auth-proxy")
        def auth_proxy():
            failed = make_response("<h1>Access denied!</h1>", 401)
            failed.set_cookie("protocol", "")
            failed.set_cookie("ip", "")
            failed.set_cookie("port", "")
            
            if "protocol" not in request.cookies or "ip" not in request.cookies or "port" not in request.cookies:
                return failed
            
            ip = request.cookies.get("ip")
            #print(request.headers)
            for service in self.SERVICES:
                if ip == service['ip'] and service['enabled'] and service['login_enabled']:
                    if service['allowed_referers'] == []: 
                        return make_response("<h1>You aren't supposed to be here!</h1>", 200)
                    else:
                        if "Referer" in request.headers:
                            print(request.headers["Referer"])
                        referer_found = False
                        for referer in service['allowed_referers']:
                            if ip == service['ip'] and service['enabled'] and service['login_enabled'] and "Referer" in request.headers and request.headers["Referer"].endswith(referer):                
                                return make_response("<h1>You aren't supposed to be here!</h1>", 200)
                        if not referer_found:
                            return failed
            
            if "id" not in session or not self.check_session():
                return failed
            
           
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


    def compare_sessions(self, time_old: datetime, time_new: datetime) -> bool:
        return time_new - time_old < timedelta(minutes=self.session_length)


    def check_session(self) -> bool:
        from_db = self.cache_db.get_session_from_db(session["id"])
        if len(from_db) == 0:
            return False 
        return self.compare_sessions(from_db[2], current_time_dt())


    def create_session(self, username: str):
        session["id"] = self.cache_db.add_session_to_db(username=username)


    def invalidate_session(self):
        if "id" in session:
            self.cache_db.remove_session_from_db(session["id"])
        session.pop("id", None)
        r = make_response(redirect(url_for("login")))
        r.set_cookie("session", "")
        return r