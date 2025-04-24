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
from utils.AuthOpenID import AuthOpenID
from os import urandom


class Auth:
    def __init__(self, args):
        self.app = args.app
        self.proxmox_data_cache = args.proxmox_data_cache
        self.system_config = args.system_config
        self.cache_db = args.cache_db

        self.auth_methods=args.auth_methods

        self.session_length = int(self.system_config['session_length'])  # minutes
        self.pve_nets = self.system_config['proxmox_webapp']['pve_nets']

        self.SERVICES = self.system_config['services']

        self.register_routes()
        
    def verify_user_can_access_ip(self, ip: str):
        ip_is_in_pve_net = False
        for pve_net in self.pve_nets:
            if pve_net in ip:
                ip_is_in_pve_net = True
        if not ip_is_in_pve_net:
            return True
        
        username = self.cache_db.get_session_from_db(session["id"])[0]
        
        if ip not in self.proxmox_data_cache:
            # need to check db
            print(f"ip {ip} not in vm ip cache, going to db")
            if self.cache_db.check_ip(username, ip):
                self.proxmox_data_cache[ip] = [username]
                return True
            self.proxmox_data_cache[ip] = []
            return False
        
        if username in self.proxmox_data_cache[ip]:
            return True # found ip in cache at username
        
        #print(f"{username} not in cache for {ip}")
        
        if self.cache_db.check_ip(username, ip):
            self.proxmox_data_cache[ip].append(username)
            return True
        return False
    
    def return_login_page(self, page="login", extra_content=""):
        return make_response(
            render_template("login.html", page=page, extra_content=extra_content, banner=banner, services=self.SERVICES, auth_methods=self.auth_methods)
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
                if auth_method.type == "openid":
                    continue
                if auth_method.authenticate_user(username=username, password=password):
                    print(f"authenticated {username} with {auth_method.type}")
                    self.create_session(username=username)
                    return redirect(url_for("index"))

            r = self.return_login_page(page="login", extra_content="Incorrect username or password")
            r.set_cookie("session", "")
            return r

        @self.app.route("/web/openid/<string:name>")
        def openid_login(name: str):
            for auth_method in self.auth_methods:
                if not isinstance(auth_method, AuthOpenID):
                    continue
                if auth_method.name != name:
                    continue
                redirect_uri = auth_method.base_redirect_domain + f"/web/openid/{name}/auth"
                nonce = urandom(16).hex()
                session["openid_nonce"] = nonce
                return auth_method.oauth.openid.authorize_redirect(
                    redirect_uri,
                    nonce=nonce
                )
            return self.invalidate_session()
        
        @self.app.route("/web/openid/<string:name>/auth")
        def openid_auth(name: str):
            for auth_method in self.auth_methods:
                if not isinstance(auth_method, AuthOpenID):
                    continue
                if auth_method.name != name:
                    continue
                
                nonce = session.pop("openid_nonce", None)
                if not nonce:
                    return self.invalidate_session()
                token = auth_method.oauth.openid.authorize_access_token()
                user_info = auth_method.oauth.openid.parse_id_token(token, nonce)

                username = user_info['preferred_username']
                self.create_session(username=username, openid=True)
                return redirect(url_for("index"))
            return redirect(url_for('login'))
        
        @self.app.route("/web/update_session", methods=["GET"])
        def update_session_route():
            self.cache_db.update_session_in_db(session['id'])
            return "done"

        @self.app.route("/web/logout")
        def logout():
            from_db = self.cache_db.get_session_from_db(session["id"])
            if from_db[3]: # 3 is the openid bool in db
                for auth_method in self.auth_methods:
                    if auth_method.type == "openid":
                        return self.invalidate_session(auth_method.logout_url)
            return self.invalidate_session()

        @self.app.route("/auth-proxy")
        def auth_proxy():
            failed = make_response("<h1>Access denied!</h1>", 401)
            failed.set_cookie("protocol", "")
            failed.set_cookie("ip", "")
            failed.set_cookie("port", "")
            
            if "protocol" not in request.cookies or "ip" not in request.cookies or "port" not in request.cookies:
                return failed
            
            protocol = request.cookies.get("protocol")
            ip = request.cookies.get("ip")
            port = request.cookies.get("port")
            #print(request.headers)
            for service in self.SERVICES: # services that don't need login
                if ip in service['ips'] and service['enabled'] and not service['needs_login'] and service['port'] == port and service['protocol'] == protocol:
                    if service['allowed_referers'] == []: 
                        return make_response("<h1>You aren't supposed to be here!</h1>", 200)
                    else:
                        #if "Referer" in request.headers:
                            #(request.headers["Referer"])
                        referer_found = False
                        for referer in service['allowed_referers']:
                            if ip in service['ips'] and service['enabled'] and not service['needs_login'] and "Referer" in request.headers and request.headers["Referer"].endswith(referer):                
                                return make_response("<h1>You aren't supposed to be here!</h1>", 200)
                        if not referer_found:
                            return failed
            
            if "id" not in session or not self.check_session():
                return failed
            
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


    def create_session(self, username: str, openid=False):
        session["id"] = self.cache_db.add_session_to_db(username=username, openid=openid)


    def invalidate_session(self, openid_logout_url=None):
        if "id" in session:
            self.cache_db.remove_session_from_db(session["id"])
        session.pop("id", None)
        if openid_logout_url:
            r = make_response(redirect(openid_logout_url))
        else:
            r = make_response(redirect(url_for("login")))
        r.set_cookie("session", "")
        return r