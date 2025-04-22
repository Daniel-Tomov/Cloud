from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    make_response,
    session,
    redirect,
    url_for,
)
from flask_compress import Compress
from utils.Arguments import Arguments


# TODO
# 3. Functionality to connect to regular Linux VM with GPU passthrough on Proxmox cluster/host
# - Give permission to user on the proxmox host
# - Will need to integrate logins with outside source
#   - webapp - probably not
#   - active directory
# 4. Functionality to create regular Linux VM with GPU passthrough on Proxmox host/cluster
# 6. Look into using ldap on student vms to authenticate
#   - question is, can the credentials be found once the student is given full root access to the vm?
# 10. Look into custom error pages instead of redirecting to /web/home or /web/login

class Main:
    def __init__(self):

        # Remove user page access to remove clutter from the console
        # log = logging.getLogger('werkzeug')
        # log.setLevel(logging.ERROR)

        # use flask_compress to minify resources to make page loading faster on slower networks

        # various flask settings to remove whitespace in the HTML file sent to the client after the templating is done.
        # also has various security settings to ensure hackers can not use XSS attacks to get a user's session cookie
        self.app = self.start_app()
        # app = Flask(__name__)

        arguments = Arguments(app=self.app)
        self.system_config = arguments.system_config
        
        self.app.jinja_env.trim_blocks = True
        self.app.jinja_env.lstrip_blocks = True
        self.app.config["SECRET_KEY"] = self.system_config['FLASK_SECRET_KEY']
        self.app.secret_key = self.system_config['FLASK_SECRET_KEY']
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        self.app.config["TEMPLATES_AUTO_RELOAD"] = True
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        self.app.config["SESSION_PERMANENT"] = False
        self.app.config["SESSION_TYPE"] = "filesystem"
        self.app.config["SESSION_COOKIE_NAME"] = "webapp-session"
        self.app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Strict",
        )
        self.register_routes()
        self.cache_db = arguments.cache_db
        self.auth = arguments.auth
        
        #self.app.run(host="0.0.0.0", port=5555, debug=False, use_reloader=False) # development server

    def start_app(self):
        compress = Compress()
        app = Flask(__name__)
        compress.init_app(app)
        return app

    def register_routes(self):
        # set multiple routes for index.html as user may forget the exact URL
        @self.app.route("/web/home", methods=["GET"])
        @self.app.route("/web/index", methods=["GET"])
        @self.app.route("/web/", methods=["GET"])
        #@self.app.route("/web", methods=["GET"])
        def index():
            if "id" not in session:
                return self.auth.invalidate_session()
            if not self.auth.check_session():
                return self.auth.invalidate_session()

            self.cache_db.update_session_in_db(session["id"])
            
            return make_response(render_template("index.html", services=self.system_config['services'], vm_provision_options=self.system_config['vm-provision-options']))

        @self.app.errorhandler(404)
        def not_found(error):
            resp = make_response("404", 404)
            return resp
        
        @self.app.route("/web/open/<string:protocol>/<string:ip>/<string:port>", methods=["GET"])
        def open(protocol: str, ip: str, port: str):
            r = redirect("/") # make_response(render_template("redirect.html", url="/"))
            r.set_cookie("protocol", protocol)
            r.set_cookie("ip", ip)
            r.set_cookie("port", port)
            #print(f'{protocol} {ip} {port}')
            return r
        
        @self.app.route("/web/open/<string:requesed_service>", methods=["GET"])
        def open_service(requesed_service):
            for service in self.system_config['services']:
                if service['id'] == requesed_service:
                    r = redirect(service['url']) # make_response(render_template("redirect.html", url=service['url']))
                    r.set_cookie("protocol", service['protocol'])
                    r.set_cookie("ip", service['ip'])
                    r.set_cookie("port", service['port'])
                    return r
                
            return redirect(url_for('index'))
        
http = Main().app
