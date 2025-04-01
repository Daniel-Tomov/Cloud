from requests import get
from os import getenv
from flask import (
    Flask,
    session,
    request,
)
from json import loads
from utils.utils import sanitize_input
from queue import Queue
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from urllib.parse import quote_plus as urlencode

class Proxmox:
    def __init__(self, args):
        self.app = args.app
        self.proxmox_data_cache = args.proxmox_data_cache
        self.system_config = args.system_config
        self.cache_db = args.cache_db
        self.auth = args.auth


        self.PROXMOX_WEBAPP_HOST = args.system_config['proxmox_webapp']['host']
        self.PROXMOX_WEBAPP_verify_ssl = args.system_config['proxmox_webapp']['verifyssl']
        if not self.PROXMOX_WEBAPP_verify_ssl:
            disable_warnings(InsecureRequestWarning)


        self.register_endpoints()

    def register_endpoints(self):
        @self.app.route("/web/get_vm_status", methods=["GET"])
        def get_vm_status():
            if "id" not in session or not self.auth.check_session():
                return {"logout": True}
            
            username = self.cache_db.get_session_from_db(session['id'])[0]

            try:
                r = get(
                    url=f"{self.PROXMOX_WEBAPP_HOST}/get_vm_status/{username}",
                    verify=self.PROXMOX_WEBAPP_verify_ssl,
                ).json()
            except Exception as e:
                print(e)
                return {"result": "proxmox communication server is down"}

            for vm in r: # update the VM IP cache
                if "ip" in r[vm] and r[vm]["ip"] != "":
                    self.proxmox_data_cache[r[vm]["ip"]] = r[vm]["tags"].split(";")
                    self.cache_db.set_vm_ip_map(r[vm]["ip"], r[vm]["tags"])
            return r
        @self.app.route("/web/set_vm_power_state", methods=["POST"])
        def set_vm_power_state():
            if "id" not in session or not self.auth.check_session():
                return {"logout": True}
            data = request.json
            try:
                if request.json == None:
                    return {"result": "fail"}
                if request.json == {}:
                    return {"result": "fail"}
                if "power_value" not in request.json:
                    return {"result": "fail"}
                if "vmid" not in request.json:
                    return {"result": "fail"}
                if "node" not in request.json:
                    return {"result": "fail"}
            except Exception:
                return {"result": "fail"}
                

            node = sanitize_input(data["node"], "-")
            vmid = sanitize_input(data["vmid"], "/")
            power_value = sanitize_input(data["power_value"])

            if "//" in vmid:
                return {"result": "fail"}
            
            username = self.cache_db.get_session_from_db(session["id"])[0]
            return {
                "result": get(
                    url=f"{self.PROXMOX_WEBAPP_HOST}/set_vm_power_state/{username}/{node}/{vmid}/{power_value}",
                    verify=self.PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

        @self.app.route("/web/add_tag", methods=["POST"])
        def add_tag():
            if "id" not in session:
                return {"logout": "id not in session"}

            if not self.auth.check_session():
                return {"logout": "invalid session"}
            
            try:
                if request.json == None:
                    return {"result": "fail"}
                if request.json == {}:
                    return {"result": "fail"}
                if "username" not in request.json:
                    return {"result": "fail"}
                if "vmid" not in request.json:
                    return {"result": "fail"}
                if "node" not in request.json:
                    return {"result": "fail"}
            except Exception:
                return {"result": "fail"}
            
            data = request.json
            
            username = self.cache_db.get_session_from_db(session["id"])[0]
            username_to_add = sanitize_input(data["username"])

            if username_to_add == None:
                return {"result": "fail"}
            vmid = sanitize_input(data["vmid"], "/")
            node = sanitize_input(data["node"], "-")

            return {
                "result": get(
                    url=f"{self.PROXMOX_WEBAPP_HOST}/add_tag/{username}/{node}/{vmid}/{username_to_add}",
                    verify=self.PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

        @self.app.route("/web/remove_tag", methods=["POST"])
        def remove_tag():
            if "id" not in session or not self.auth.check_session():
                return {"logout": True}

            try:
                if request.json == None:
                    return {"result": "fail"}
                if request.json == {}:
                    return {"result": "fail"}
                if "username" not in request.json:
                    return {"result": "fail"}
                if "vmid" not in request.json:
                    return {"result": "fail"}
                if "node" not in request.json:
                    return {"result": "fail"}
            except Exception:
                return {"result": "fail"}
            data = request.json
            
            
            username = self.cache_db.get_session_from_db(session["id"])[0]
            
            username_to_remove = sanitize_input(data["username"])
            vmid = sanitize_input(data["vmid"], "/")
            node = sanitize_input(data["node"], "-")

            return {
                "result": get(
                    url=f"{self.PROXMOX_WEBAPP_HOST}/remove_tag/{username}/{node}/{vmid}/{username_to_remove}",
                    verify=self.PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

        @self.app.route("/web/create_vm", methods=["POST"])
        def create_vm():
            if "id" not in session or not self.auth.check_session():
                return {"logout": True}

            username = self.cache_db.get_session_from_db(session["id"])[0]
            try:
                if request.json == None:
                    return {"result": "fail"}
                if request.json == {}:
                    return {"result": "fail"}
                if "password" not in request.json or "id" not in request.json:
                    return {"result": "fail"}
            except Exception:
                return {"result": "fail"}
            
            if request.json['id'] not in self.system_config['vm-provision-options']:
                return {"result": "fail"}
            

            vm_type = request.json['id']
            password = urlencode(request.json["password"])


            if vm_type == "request":
                print("got request")
                print(password)
                self.cache_db.add_request_to_db(username, password)
                return {"result": "You will be contacted when your VM is created or if we have further questions."}

            does_have_personal_vm_created = get(
                url=f"{self.PROXMOX_WEBAPP_HOST}/does_have_personal_vm_created/{vm_type}/{username}",
                verify=self.PROXMOX_WEBAPP_verify_ssl,
            ).json()["result"]
            if does_have_personal_vm_created:
                return {"result": "VM is already created"}


            
            return {
                "result": get(
                    url=f"{self.PROXMOX_WEBAPP_HOST}/create_vm/{vm_type}/{username}/{password}",
                    verify=self.PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

if __name__ == "__main__":
    """"""
