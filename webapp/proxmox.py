from requests import get
from dotenv import load_dotenv
from os import getenv
from flask import (
    Flask,
    session,
    request,
)
from json import loads
from auth import check_session
from db import get_session_from_db, set_vm_ip_map
from utils import sanitize_input
from queue import Queue
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from urllib.parse import quote_plus as urlencode


load_dotenv()
PROXMOX_WEBAPP_HOST = getenv("PROXMOX_WEBAPP_HOST")
PROXMOX_WEBAPP_verify_ssl = getenv("PROXMOX_WEBAPP_verify_ssl", "False") == "True"
if not PROXMOX_WEBAPP_verify_ssl:
    disable_warnings(InsecureRequestWarning)

class Proxmox:
    def __init__(self, app: Flask, proxmox_data_cache: dict):
        self.app = app
        self.proxmox_data_cache = proxmox_data_cache

        self.register_endpoints()

    def register_endpoints(self):
        @self.app.route("/web/get_vm_status", methods=["GET"])
        def get_vm_status():
            if "id" not in session or not check_session():
                return {"logout": True}
            
            username = get_session_from_db(session['id'])[0]

            try:
                r = get(
                    url=f"{PROXMOX_WEBAPP_HOST}/get_vm_status/{username}",
                    verify=PROXMOX_WEBAPP_verify_ssl,
                ).json()
            except Exception:
                return {"result": "proxmox communication server is down"}

            for vm in r: # update the VM IP cache
                if "ip" in r[vm] and r[vm]["ip"] != "":
                    self.proxmox_data_cache[r[vm]["ip"]] = r[vm]["tags"].split(";")
                    set_vm_ip_map(r[vm]["ip"], r[vm]["tags"])
            return r
        @self.app.route("/web/set_vm_power_state", methods=["POST"])
        def set_vm_power_state():
            if "id" not in session or not check_session():
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
                

            node = sanitize_input(data["node"])
            vmid = sanitize_input(data["vmid"], "/")
            power_value = sanitize_input(data["power_value"])

            if vmid is None or power_value is None or node is None:
                return {"result": "fail"}
            username = get_session_from_db(session["id"])[0]
            return {
                "result": get(
                    url=f"{PROXMOX_WEBAPP_HOST}/set_vm_power_state/{username}/{node}/{vmid}/{power_value}",
                    verify=PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

        @self.app.route("/web/add_tag", methods=["POST"])
        def add_tag():
            if "id" not in session:
                return {"logout": "id not in session"}

            if not check_session():
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
            
            username = get_session_from_db(session["id"])[0]
            username_to_add = sanitize_input(data["username"])

            if username_to_add == None:
                return {"result": "fail"}
            vmid = sanitize_input(data["vmid"])
            node = sanitize_input(data["node"])

            return {
                "result": get(
                    url=f"{PROXMOX_WEBAPP_HOST}/add_tag/{username}/{node}/{vmid}/{username_to_add}",
                    verify=PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

        @self.app.route("/web/remove_tag", methods=["POST"])
        def remove_tag():
            if "id" not in session or not check_session():
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
            
            
            username = get_session_from_db(session["id"])[0]
            
            username_to_remove = sanitize_input(data["username"])
            vmid = sanitize_input(data["vmid"])
            node = sanitize_input(data["node"])

            return {
                "result": get(
                    url=f"{PROXMOX_WEBAPP_HOST}/remove_tag/{username}/{node}/{vmid}/{username_to_remove}",
                    verify=PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

        @self.app.route("/web/create_vm", methods=["POST"])
        def create_vm():
            if "id" not in session or not check_session():
                return {"logout": True}

            username = get_session_from_db(session["id"])[0]
            try:
                if request.json == None:
                    return {"result": "fail"}
                if request.json == {}:
                    return {"result": "fail"}
                if "password" not in request.json:
                    return {"result": "fail"}
            except Exception:
                return {"result": "fail"}

            does_have_personal_vm_created = get(
                url=f"{PROXMOX_WEBAPP_HOST}/does_have_personal_vm_created/{username}",
                verify=PROXMOX_WEBAPP_verify_ssl,
            ).json()["result"]
            if does_have_personal_vm_created:
                return {"result": "VM is already created"}

            password = urlencode(request.json["password"])
            
            return {
                "result": get(
                    url=f"{PROXMOX_WEBAPP_HOST}/create_vm/{username}/{password}",
                    verify=PROXMOX_WEBAPP_verify_ssl,
                ).json()["result"]
            }

if __name__ == "__main__":
    """"""
