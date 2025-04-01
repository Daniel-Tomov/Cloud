from utils.db.CacheDB import CacheDB
from utils.db.AuthDB import AuthDB
from yaml import safe_load
from flask import Flask
from Auth import Auth
from Proxmox import Proxmox
from utils.LDAPHandler import LDAPHandler

class Arguments:
    def __init__(self, app: Flask):
        self.app = app
        self.proxmox_data_cache = {}
        with open('../../vm-options.yaml', 'r') as config:
            self.system_config = safe_load(config)

        self.auth_methods = []
        for authentication_method in self.system_config['authentication']:
            name = next(iter(authentication_method.keys()))
            authentication_method = authentication_method[name]
            if authentication_method['type'] == 'postgres' and authentication_method['enabled']:
                self.auth_methods.append(AuthDB(authentication_method, args=self))
            if authentication_method['type'] == 'ldap' and authentication_method['enabled']:
                #print(authentication_method)
                self.auth_methods.append(LDAPHandler(ldap_config=authentication_method))


        self.cache_db = CacheDB(args=self)
        self.auth = Auth(args=self)
        self.proxmox = Proxmox(args=self)

