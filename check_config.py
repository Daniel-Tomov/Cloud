from yaml import safe_load


with open('vm-options.yaml.sample', 'r') as config:
    system_config = safe_load(config)

if not system_config:
    print("Could not load system config")
    exit(0)

errors = ""

keys = ['FLASK_SECRET_KEY', 'PYTHONWARNINGS', 'session_length', 'session_cookie_name']
for k in keys:
    if k not in system_config:
        errors += f"Could not load {k}\n"

#========================================================================================================
if 'proxmox_nodes' in system_config:
    if 'authentication_type' in system_config['proxmox_nodes']:
        if system_config['proxmox_nodes']['authentication_type'] == "credentials" or system_config['proxmox_nodes']['authentication_type'] == "token":
            pass
        else:
            errors += "proxmox_nodes.authentication_type is not credentials or token"
    else:
        errors += "Could not load proxmox_nodes.authentication_type.\n"

    keys = ['verify_ssl', 'nodes', 'prod_nodes_contain', 'user_group', 'check_node']
    for k in keys:
        if k not in system_config['proxmox_nodes']:
            errors += f"Could not load proxmox_nodes.{k}\n"
            continue

        if k == 'nodes':
            if not isinstance(system_config['proxmox_nodes']['nodes'], list):
                errors += "proxmox_nodes.nodes is not list"
else:
    errors += "Could not load proxmox_nodes.\n"

#======================================================================================================

if "proxmox_webapp" in system_config:
    keys = ['host', 'verifyssl', 'pve_nets']
    for k in keys:
        if k not in system_config['proxmox_webapp']:
            errors += f"Could not load proxmox_webapp.{k}\n"
else:
    errors += "Could not load proxmox_webapp.\n"

#======================================================================================================

if 'cache_database' in system_config:
    keys = ['user', 'password', 'database', 'host', 'port', 'sslmode']
    for k in keys:
        if k not in system_config['cache_database']:
            errors += f"Could not load cache_database.{k}\n"
else:
    errors += "Could not load cache_database."

#=========================================================================================================

if "authentication" in system_config:
    if not isinstance(system_config['authentication'], list):
        errors += "authentication is not a list\n"
    else:
        method_num = 0
        for method in system_config['authentication']:
            method_num += 1
            if not isinstance(method, dict):
                errors += f"authentication method {method_num} is not dict\n"
                continue

            name = next(iter(method.keys()))
            method = method[name]
            if not isinstance(method, dict):
                errors += f"authentication.{name} is not dict\n"
                continue
            if "type" not in method:
                errors += f"could not find authentication.{name}\n"
                continue
            if method['type'] == 'postgres':
                keys = ['user', 'password', 'database', 'host', 'port', 'sslmode', 'realm']
                for k in keys:
                    if k not in method:
                        errors += f"Could not load authentication.{name}.{k}\n"
            elif method['type'] == "ldap":
                keys = ['servers', 'port', 'domain', 'bind-user', 'user-filter', 'base-dn', 'bind-password', 'realm']
                for k in keys:
                    if k not in method:
                        errors += f"Could not load authentication.{name}.{k}\n"
            elif method['type'] == "openid":
                keys = ['name', 'ssl_verify', 'client_id', 'client_secret', 'base_redirect_domain', 'metadata_url', 'logout_url', 'realm']
                for k in keys:
                    if k not in method:
                        errors += f"Could not load authentication.{name}.{k}\n"

            if "enabled" not in method:
                errors += "Could not load authentication"
else:
    errors += "Could not load authentication"

#======================================================================================================================================

keys = ['id', 'name', 'enabled', 'needs_login', 'protocol', 'ips', 'port', 'url', 'allowed_referers']
if 'services' in system_config:
    num = 0
    for method in system_config['services']:
        num += 1
        if not isinstance(method, dict):
            errors += f'Service {num} is not dict\n'
            continue
        for k in keys:
            if k not in method:
                errors += f"Could not load services.{num}.{k}\n"
                continue
            if k == "ips":
                if not isinstance(method['ips'], list):
                    errors += f"services.{num}.ips is not list\n"
            if k == "allowed_referers":
                if not isinstance(method['allowed_referers'], list) and method['allowed_referers'] != None:
                    print(method['allowed_referers'])
                    errors += f"services.{num}.allowed_referers is not list\n"
else:
    errors += "Could not load services"

#===============================================================================================================================
keys = ['enabled', 'option', 'name', 'input_label', 'description', 'cores', 'cpu', 'memory', 'networks', 'iso', 'iso_location', 'storage', 'storage_location', 'bios', 'sockets', 'start', 'numa', 'agent', 'scsihw', 'balloon', 'pool', 'needs_postinst']
proxmox_keys = ['lvm_max_root', 'proxmox_webapp_url', 'proxmox_webapp_fingerprint', 'images', 'user_vlan', 'provision_vlan']
proxmox_images_keys = ['image_url', 'image_url_verifyssl', 'cores', 'cpu', 'memory', 'networks', 'iso', 'iso', 'storage', 'storage_location', 'start', 'bios', 'sockets', 'numa', 'scsihw', 'balloon']
request_keys = ['enabled', 'option', 'name', 'input_label', 'description']

if 'vm-provision-options' in system_config:
    if not isinstance(system_config['vm-provision-options'], dict):
        errors += "vm-provision-options is not dict\n"
        pass
    for option in system_config['vm-provision-options']:
        if not isinstance(system_config['vm-provision-options'][option], dict):
            errors += f'vm-provision-options.{option} is not dict\n'
            continue
        if option == 'request':
            for k in request_keys:
                if k not in system_config['vm-provision-options'][option]:
                    errors += f"Could not load vm-provision-options.{option}.{k}\n"
                    continue
            continue
        for k in keys:
            if k not in system_config['vm-provision-options'][option]:
                errors += f"Could not load vm-provision-options.{option}.{k}\n"
                continue
            if k == "networks":
                if not isinstance(system_config['vm-provision-options'][option]['networks'], list):
                    errors += f"vm-provision-options.{option}.networks is not list\n"

        if "images" in system_config['vm-provision-options'][option]: # option is proxmox vm
            if not isinstance(system_config['vm-provision-options'][option]['images'], dict):
                errors += f"vm-provision-options.{option}.images is not dict\n"
                continue

            for pk in proxmox_keys:
                if pk not in system_config['vm-provision-options'][option]:
                    errors += f"Could not load vm-provision-options.{option}.{pk}\n"
                    
            
            for image in system_config['vm-provision-options'][option]['images']:
                if not isinstance(system_config['vm-provision-options'][option]['images'][image], dict):
                    errors += f"vm-provision-options.{option}.images.{image} is not dict\n"
                    continue

                    
else:
    errors += "Could not load vm-provision-options"

if errors == "":
    print("No errors.")
    exit(0)
else:
    print(errors)
    exit(1)