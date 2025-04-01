import ldap
from flask import current_app
from yaml import safe_load

class LDAPHandler(object):
    def __init__(self, ldap_config: dict):
        self.servers = ldap_config.get('servers', [])
        self.port = ldap_config.get('port', 389)
        self.domain = ldap_config.get('domain')
        self.bind_user = ldap_config.get('bind-user')
        self.user_filter = ldap_config.get('user-filter')
        self.base_dn  = ldap_config.get('base-dn')
        self.bind_password = ldap_config.get('bind-password')

    def authenticate_user(self, username: str, password: str) -> bool:
        for server in self.servers:
            try:
                ldap_connection_bind = ldap.initialize(f'ldap://{server}:{self.port}')
                # Separate Bind with Bind account and Bind with user account
                ldap_connection_user = ldap.initialize(f'ldap://{server}:{self.port}')
                # Bind with the bind user
                ldap_connection_bind.simple_bind_s(self.bind_user, self.bind_password)
                # Attempt authentication with the passed username and password
                user_dn = f'CN={username},{self.base_dn}'
                ldap_connection_user.simple_bind_s(user_dn, password)

                # Check if the authenticated user matches the user-filter
                filter_result =  self.check_user_filter(ldap_connection_bind, username, self.user_filter)
                if filter_result:
                    return filter_result

            except ldap.INVALID_CREDENTIALS as e:
                # Invalid credentials, continue to the next server
                pass
            except ldap.LDAPError as e:
                current_app.logger.error(f"LDAP Error: {e}")
            finally:
                ldap_connection_bind.unbind()
                ldap_connection_user.unbind()

        # Authentication failed on all servers
        return False

    def check_user_filter(self, ldap_connection: ldap, username: str, user_filter: str):
        try:
            result = ldap_connection.search_s(
                base=f'{self.base_dn}',
                scope=ldap.SCOPE_SUBTREE,
                filterstr=f'(&(cn={username}){user_filter})',
                attrlist=['sAMAccountName','givenName','sn']  # Include any additional attributes you need
            )
            return result
        except ldap.LDAPError as e:
            current_app.logger.error(f"Error checking user filter: {e}")
            return False


if __name__ == "__main__":
    with open('../vm-options.yaml', 'r') as config:
        system_config = safe_load(config)
    for authentication_method in system_config['authentication']:
        name = next(iter(authentication_method.keys()))
        authentication_method = authentication_method[name]
        if authentication_method['type'] == 'ldap':
            if authentication_method['enabled']:
                handler = LDAPHandler(ldap_config=authentication_method)
                result = handler.authenticate_user("", "")
                print(result)