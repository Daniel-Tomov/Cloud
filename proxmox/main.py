from flask import Flask, request
from flask_compress import Compress
from os import getenv, urandom
from random import choice
from proxmox import (
    create_vm,
    get_user_vms,
    does_user_own_vm,
    post_endpoint,
    get_endpoint,
    put_endpoint,
    recieve_postinst_ip,
    send_answer_toml,
    status,
    QueueEntry,
    vm_creation_queue,
    does_have_personal_vm_created,
    send_first_boot_get,
    set_vm_power
)
from utils import system_config
from VMShutdown import VMShutdown
from vlan import VLAN

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
        self.app.jinja_env.trim_blocks = True
        self.app.jinja_env.lstrip_blocks = True
        self.app.config["SECRET_KEY"] = system_config['FLASK_SECRET_KEY']
        self.app.secret_key = system_config['FLASK_SECRET_KEY']
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        self.app.config["TEMPLATES_AUTO_RELOAD"] = True
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        self.app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Strict",
        )

        self.register_endpoints()
        self.vmshutdown = VMShutdown(system_config)
        if system_config['proxmox_nodes']['vlans']['enabled']:
            VLAN(self.app, system_config)
        #self.app.run(host="0.0.0.0", port=5556, debug=False, use_reloader=False, ssl_context='adhoc') # development server

    def start_app(self):
        compress = Compress()
        app = Flask(__name__)
        compress.init_app(app)
        return app

    def register_endpoints(self):
        @self.app.route("/create_vm/<string:vm_type>/<string:username>/<string:password>")
        def create_vm_route(vm_type:str, username: str, password: str):
            has_vm = does_have_personal_vm_created(vm_type=vm_type, username=username)
            if has_vm:
                return {"result": "VM is already created"}
            # choose a node
            nodes = []
            #print(status)
            for entry in status:
                if "node" in entry and "type" in entry and entry["type"] == "node" and entry["node"] not in nodes and system_config['proxmox_nodes']['prod_nodes_contain'] in entry["node"]:
                    nodes.append(entry["node"])

            node = choice(nodes)
            vm_creation_queue.put(QueueEntry(username=username, root_password=password, vm_ip="", valid_node=node, vm_type=vm_type))

            return {"result": "success"}

        @self.app.route("/get_vm_status/<string:user>", methods=["GET"])
        def get_vm_status(user: str):
            self.vmshutdown.add_last_login_to_db(user)
            return get_user_vms(user)

        @self.app.route("/create_user/<string:realm>/<string:username>/<string:password>")
        def create_user_with_password(realm: str, username: str, password: str):
            #users = get_endpoint(endpoint="/api2/json/access/users")
            data = {"userid": f'{username}@{realm}', "password": password, "groups": "", "expire": 0, "enable": 1, "firstname": "" ,"lastname": "", "email": "", "comment": "", "keys": ""} # userid=test%40pve&password=password&groups=4002&expire=0&enable=1&firstname=first&lastname=last&email=&comment=&keys=
            create_user = post_endpoint(endpoint="/api2/extjs/access/users", data=data)
            
            return ""
        
        @self.app.route("/create_user/<string:realm>/<string:username>")
        def create_user_with_no_password(realm: str, username: str):
            #users = get_endpoint(endpoint="/api2/json/access/users")
            data = {"userid": f'{username}@{realm}', "groups": "", "expire": 0, "enable": 1, "firstname": "" ,"lastname": "", "email": "", "comment": "", "keys": ""} # userid=test%40pve&password=password&groups=4002&expire=0&enable=1&firstname=first&lastname=last&email=&comment=&keys=
            create_user = post_endpoint(endpoint="/api2/extjs/access/users", data=data)
            
            return ""
        
        
        @self.app.route(
            "/set_vm_power_state/<string:username>/<string:node>/<string:vm_type>/<string:vmid>/<string:power_value>",
            methods=["GET"],
        )
        def set_vm_power_state(
            username: str, node: str, vm_type: str, vmid: str, power_value: str
        ):
            vmid = f'{vm_type}/{vmid}'
            name, tags, node = does_user_own_vm(username=username, vmid=vmid)
            if name == "" or tags == "":
                return {"result": "you don't own this vm"}
            set_vm_power(node=node, vmid=vmid, power_value=power_value)
            
            return {"result": "success"}

        @self.app.route(
            "/add_tag/<string:username>/<string:node>/<string:vm_type>/<string:vmid>/<string:username_to_add>",
            methods=["GET"],
        )
        def add_tag(
            username: str, node: str, vm_type: str, vmid: str, username_to_add: str
        ):
            vmid = f'{vm_type}/{vmid}'  # qemu/123 is passed to the request so need to recombine them
            name, tags, node = does_user_own_vm(username=username, vmid=vmid)  # returns "" if the user does not own the vm
            if name == "":
                return {"result": "You don't own this VM"}

            if username_to_add in tags.split(";"):
                return {"result": "name already added"}

            tags = tags + ";" + username_to_add
            data = {"tags": tags}
            #print(f'adding {username_to_add}')
            
            #groups = get_endpoint(endpoint="/api2/json/access/groups")
            #user_groups = get_endpoint(endpoint="/api2/extjs/access/users/dtomo001%40CybAdm")
            #domains = get_endpoint(endpoint="/api2/json/access/domains")
            users = get_endpoint("/api2/json/access/users?full=1")
            for user in users:
                if user['userid'].split("@")[0] == username_to_add:
                    groups = user['groups'].split(",")
                    groups.append(vmid.split("/")[1])
                    groups = ','.join(groups)
                    realm = user['userid'].split("@")[1]
                    r = put_endpoint(f"/api2/extjs/access/users/{username_to_add}@{realm}", data={"groups": groups})
                
            return {"result": put_endpoint(endpoint=f"/api2/extjs/nodes/{node}/{vmid}/config", data=data)}

        @self.app.route(
            "/remove_tag/<string:username>/<string:node>/<string:vm_type>/<string:vmid>/<string:username_to_remove>",
            methods=["GET"],
        )
        def remove_tag(
            username: str, node: str, vm_type: str, vmid: str, username_to_remove: str
        ):
            vmid = f'{vm_type}/{vmid}'  # qemu/123 is passed to the request so need to recombine them
            name, tags, node = does_user_own_vm(username=username, vmid=vmid)  # returns "" if the user does not own the vm
            if name == "":
                return {"result": "You don't own this VM"}

            if username_to_remove == username:
                return {"result": "cannot remove your own name"}
            
            if username_to_remove not in tags.split(";"):
                return {"result": "username is not in tags"}

            users = get_endpoint("/api2/json/access/users?full=1")
            for user in users:
                if user['userid'].split("@")[0] == username_to_remove:
                    groups = user['groups'].split(",")
                    groups.remove(vmid.split("/")[1])
                    groups = ','.join(groups)
                    realm = user['userid'].split("@")[1]
                    r = put_endpoint(f"/api2/extjs/access/users/{username_to_remove}@{realm}", data={"groups": groups})
            
            
            tags = tags.split(";")
            tags.remove(username_to_remove)
            tags = ";".join(tags)
            data = {"tags": tags}
            
            return {"result": put_endpoint(endpoint=f"/api2/extjs/nodes/{node}/{vmid}/config", data=data)}
                    

        @self.app.route("/first-boot.sh", methods=["GET"])
        def first_boot_get():
            return send_first_boot_get()

        @self.app.route("/answer.toml", methods=["GET", "POST"])
        def answer_toml():
            if request.method == "GET":
                print("Got GET on /postinst")
                return ""
            return send_answer_toml()
        
        @self.app.route("/postinst", methods=["POST"])
        def postinst():
            print("got postinst")
            recieve_postinst_ip()
            return {}            

http = Main().app