from authlib.integrations.flask_client import OAuth


class AuthOpenID:
    def __init__ (self, openid_config: dict, app):
        self.oauth = OAuth(app)
        self.type = openid_config['type']
        self.name = openid_config['name']
        self.base_redirect_domain = openid_config['base_redirect_domain']
        self.metadata_url = openid_config['metadata_url']
        self.logout_url = openid_config['logout_url']
        self.realm = openid_config['realm']
        
        
        self.oauth.register(
            name="openid",
            client_id=openid_config['client_id'],
            client_secret=openid_config['client_secret'],
            server_metadata_url=openid_config['metadata_url'],
            client_kwargs={'verify': openid_config['ssl_verify'], "scope": "openid profile email"},
        )
