from flask import Flask
from flask_compress import Compress
from os import getenv, urandom
from db import (
    check_password_against_db,
    does_user_exist_in_db,
    add_user_to_db,
    add_session_to_db,
    get_session_from_db,
    remove_session_from_db,
    update_session_in_db,
)


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
        self.register_routes()
        self.app.run(host="0.0.0.0", port=5557, debug=False, use_reloader=False)

    def start_app(self):
        compress = Compress()
        app = Flask(__name__)
        compress.init_app(app)
        return app

    def register_routes(self):
        @self.app.route(
            "/check_password_against_db/<string:username>/<string:password>"
        )
        def check_password_against_db_route(username: str, password: str):
            return {
                "result": check_password_against_db(
                    username=username, password=password
                )
            }

        @self.app.route("/does_user_exist_in_db/<string:username>")
        def does_user_exist_in_db_route(username: str):
            return {"result": does_user_exist_in_db(username=username)}

        @self.app.route("/add_user_to_db/<string:username>/<string:password>")
        def add_user_to_db_route(username: str, password: str):
            add_user_to_db(username=username, password=password)
            return {"result": "success"}

        @self.app.route("/add_session_to_db/<string:username>")
        def add_session_to_db_route(username: str):
            return {"result": add_session_to_db(username=username)}

        @self.app.route("/get_session_from_db/<string:id>")
        def get_session_from_db_route(id: str):
            return {"result": get_session_from_db(id=id)}

        @self.app.route("/update_session_in_db/<string:id>")
        def update_session_in_db_route(id: str):
            update_session_in_db(id=id)
            return {"result": "success"}

        @self.app.route("/remove_session_from_db/<string:id>")
        def remove_session_from_db_route(id: str):
            remove_session_from_db(id=id)
            return {"result": "success"}


if __name__ == "__main__":
    Main()
