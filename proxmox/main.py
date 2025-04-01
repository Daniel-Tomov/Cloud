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
    send_first_boot_get
)
from utils import system_config

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
        #self.app.run(host="0.0.0.0", port=5556, debug=False, use_reloader=False, ssl_context='adhoc') # development server

    def start_app(self):
        compress = Compress()
        app = Flask(__name__)
        compress.init_app(app)
        return app

    def register_endpoints(self):
        @self.app.route("/create_vm/<string:vm_type>/<string:username>/<string:password>")
        def create_vm_route(vm_type:str, username: str, password: str):
            # choose a node
            nodes = []
            #print(status)
            for entry in status:
                if "node" in entry and "type" in entry and entry["type"] == "node" and entry["node"] not in nodes and system_config['proxmox_nodes']['prod_nodes_contain'] in entry["node"]:
                    nodes.append(entry["node"])

            node = choice(nodes)
            vm_creation_queue.put(QueueEntry(midas=username, root_password=password, vm_ip="", valid_node=node, vm_type=vm_type))

            return {"result": "success"}

        @self.app.route("/get_vm_status/<string:user>", methods=["GET"])
        def get_vm_status(user: str):
            return get_user_vms(user)

        @self.app.route(
            "/set_vm_power_state/<string:username>/<string:node>/<string:vm_type>/<string:vmid>/<string:power_value>",
            methods=["GET"],
        )
        def set_vm_power_state(
            username: str, node: str, vm_type: str, vmid: str, power_value: str
        ):
            vmid = f'{vm_type}/{vmid}'
            name, tags = does_user_own_vm(username=username, vmid=vmid)
            if name == "" or tags == "":
                return {"result": "you don't own this vm"}

            endpoint = f"/api2/json/nodes/{node}/{vmid}/status/{power_value}"
            print(endpoint)
            data = {}
            post_endpoint(endpoint=endpoint, data=data)
            return {"result": "success"}

        @self.app.route(
            "/add_tag/<string:username>/<string:node>/<string:vm_type>/<string:vmid>/<string:username_to_add>",
            methods=["GET"],
        )
        def add_tag(
            username: str, node: str, vm_type: str, vmid: str, username_to_add: str
        ):
            vmid = f'{vm_type}/{vmid}'  # qemu/123 is passed to the request so need to recombine them
            name, tags = does_user_own_vm(
                username=username, vmid=vmid
            )  # returns "" if the user does not own the vm
            if name == "":
                return {"result": "You don't own this VM"}

            if username_to_add in tags.split(";"):
                return {"result": "name already added"}
            endpoint = f"/api2/extjs/nodes/{node}/{vmid}/config"

            tags = tags + ";" + username_to_add
            data = {"tags": tags}
            #print(f'adding {username_to_add}')

            return {"result": put_endpoint(endpoint=endpoint, data=data)}

        @self.app.route(
            "/remove_tag/<string:username>/<string:node>/<string:vm_type>/<string:vmid>/<string:username_to_remove>",
            methods=["GET"],
        )
        def remove_tag(
            username: str, node: str, vm_type: str, vmid: str, username_to_remove: str
        ):
            vmid = f'{vm_type}/{vmid}'  # qemu/123 is passed to the request so need to recombine them
            name, tags = does_user_own_vm(
                username=username, vmid=vmid
            )  # returns "" if the user does not own the vm
            if name == "":
                return {"result": "You don't own this VM"}

            if username_to_remove == username:
                return {"result": "cannot remove your own name"}
            
            if username_to_remove not in tags.split(";"):
                return {"result": "username is not in tags"}


            endpoint = f"/api2/extjs/nodes/{node}/{vmid}/config"

            tags = tags.split(";")
            tags.remove(username_to_remove)
            tags = ";".join(tags)
            data = {"tags": tags}
            return {"result": put_endpoint(endpoint=endpoint, data=data)}
                    

        @self.app.route("/first-boot.sh", methods=["GET"])
        def first_boot_get():
            return send_first_boot_get()

        @self.app.route("/answer.toml", methods=["POST"])
        def answer_toml():
            return send_answer_toml()
        
        @self.app.route("/postinst", methods=["POST"])
        def postinst():
            print("got postinst")
            recieve_postinst_ip()
            return {}

        @self.app.route(
            "/does_have_personal_vm_created/<string:vm_type>/<string:username>", methods=["GET"]
        )
        def does_have_personal_vm_created_route(vm_type:str, username: str):
            return {"result": does_have_personal_vm_created(vm_type=vm_type, username=username)}

http = Main().app