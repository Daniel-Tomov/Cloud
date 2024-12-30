from flask import Flask, request
from flask_compress import Compress
from os import getenv, urandom
from dotenv import load_dotenv
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
    create_fw,
)
from json import loads

load_dotenv()


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
        self.app.config["SECRET_KEY"] = (
            getenv("FLASK_SECRET_KEY")
            if getenv("FLASK_SECRET_KEY") != None or getenv("FLASK_SECRET_KEY") != ""
            else urandom(16).hex()
        )
        self.app.secret_key = (
            getenv("FLASK_SECRET_KEY")
            if getenv("FLASK_SECRET_KEY") != None or getenv("FLASK_SECRET_KEY") != ""
            else urandom(16).hex()
        )
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        self.app.config["TEMPLATES_AUTO_RELOAD"] = True
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        self.app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Strict",
        )

        self.register_endpoints()
        self.app.run(host="0.0.0.0", port=5556, debug=False, use_reloader=False)

    def start_app(self):
        compress = Compress()
        app = Flask(__name__)
        compress.init_app(app)
        return app

    def register_endpoints(self):
        @self.app.route("/create_vm/<string:username>/<string:password>")
        def create_vm_route(username: str, password: str):
            # choose a node
            nodes = []
            for entry in status:
                print(status)
                if "node" in entry and entry["type"] == "node":
                    nodes.append(entry["node"])

            node = choice(nodes)
            vm_creation_queue.put(
                QueueEntry(
                    midas=username, root_password=password, vm_ip="", valid_node=node
                )
            )

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
                return {"result": "fail"}

            endpoint = f"/api2/json/nodes/{node}/{vmid}/status/{power_value}"
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

            if username_to_add in tags:
                return {"result": "name already added"}
            endpoint = f"/api2/extjs/nodes/{node}/{vmid}/config"

            tags = tags + ";" + username_to_add
            data = {"tags": tags}

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

            if username_to_remove in name:
                return {"result": "cannot remove your own name"}

            endpoint = f"/api2/extjs/nodes/{node}/{vmid}/config"

            tags = tags.replace(username_to_remove, "").replace(";;", ";")
            data = {"tags": tags}
            return {"result": put_endpoint(endpoint=endpoint, data=data)}

        @self.app.route("/postinst", methods=["POST"])
        def postinst():
            print("got postinst")
            data = request.json
            
            if data == {}:
                print("got empty data")
                return {"result": "fail"}
            print("data[\"network-interfaces\"]")
            print(data["network-interfaces"])
            print("data[\"network-interfaces\"][0]")
            print(data["network-interfaces"][0])
            try:
                ip = data["network-interfaces"][0]["address"].split("/")[0]
            except Exception as e:
                print(e)
                for i in range(0, len(data["network-interfaces"])):
                    if "address" in data["network-interfaces"][i]:
                        print(f'recieved postinst from {ip}')
                        recieve_postinst_ip(ip=ip)

            print("end of postinst route")
            return {}
                    

        @self.app.route("/first-boot.sh", methods=["GET"])
        def first_boot_get():
            return send_first_boot_get()

        @self.app.route("/answer.toml", methods=["POST"])
        def answer_toml():
            recieve_postinst_ip(ip=request.headers["X-Forwarded-For"])
            return send_answer_toml()

        @self.app.route(
            "/does_have_personal_vm_created/<string:username>", methods=["GET"]
        )
        def does_have_personal_vm_created_route(username: str):
            return {"result": does_have_personal_vm_created(username=username)}

        @self.app.route("/create_fw", methods=["GET"])
        def create_fw_route():
            return {"result": create_fw()}


if __name__ == "__main__":
    Main()
