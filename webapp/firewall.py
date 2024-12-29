from flask import Flask, jsonify, render_template, request, make_response, session
import utils
from os import getenv
from requests import get, post
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

KEY = getenv("FW_KEY")
SECRET = getenv("FW_SECRET")
FIREWALL_URL = getenv("FIREWALL_URL")
verify_ssl = getenv("verify_ssl_fw", "False") == "True"
if not verify_ssl:
    disable_warnings(InsecureRequestWarning)


class Firewall:
    def __init__(self, app: Flask):
        self.app = app
        self.register_routes()

    def register_routes(self):
        @self.app.route("/search", methods=["GET"])
        def search():
            endpoint = "/api/firewall/filter/searchRule"
            return get_endpoint(endpoint=endpoint)

        @self.app.route("/get", methods=["GET"])
        def get():
            endpoint = "/api/firewall/filter/get"
            return get_endpoint(endpoint=endpoint)

        @self.app.route("/add", methods=["POST"])
        def add():
            endpoint = "/api/firewall/filter/add_rule"
            data = {
                "rule": {
                    "enabled": "1",
                    "sequence": "2",
                    "action": "pass",
                    "quick": "1",
                    "interface": "opt4",
                    "direction": "in",
                    "ipprotocol": "inet",
                    "protocol": "any",
                    "source_net": "any",
                    "source_port": "",
                    "source_not": "0",
                    "destination_net": "any",
                    "destination_not": "0",
                    "destination_port": "",
                    "gateway": "",
                    "log": "0",
                    "categories": "",
                    "description": "Test Automation 2",
                }
            }

            return post_endpoint(endpoint=endpoint, data=data)

        @self.app.route("/delete/<string:id>", methods=["GET"])
        def delete(id: str):
            endpoint = f"/api/firewall/filter/del_rule/{id}"
            data = {}
            return utils.post_endpoint(endpoint=endpoint, data=data)

        @self.app.route("/toggle/<string:id>", methods=["GET"])
        def toggle(id: str):
            endpoint = f"/api/firewall/filter/toggle_rule/{id}"
            data = {}
            return utils.post_endpoint(endpoint=endpoint, data=data)


def get_endpoint(endpoint: str) -> dict:
    r = get(f"https://{FIREWALL_URL}{endpoint}", auth=(KEY, SECRET))
    return r.json()


def post_endpoint(endpoint: str, data: dict) -> dict:
    r = post(f"https://{FIREWALL_URL}{endpoint}", auth=(KEY, SECRET), json=data)
    return r.json()
