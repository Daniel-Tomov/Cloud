from requests import get, post, put
from threading import Thread
from time import sleep
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from queue import Queue
from utils import system_config
from random import choice



verify_ssl = system_config['proxmox_nodes']['verify_ssl']
if not verify_ssl:
    disable_warnings(InsecureRequestWarning)


vm_creation_queue = Queue()
ready_for_vm_creation = True

first_boot_file = open("first-boot.sh").read()
answer_file = open("answer.toml").read()


class QueueEntry:
    def __init__(
        self,
        username: str = "doesnotexistuser",
        root_password: str = "password",
        vm_ip: str = "",
        valid_node: str = "",
        vm_type: str = "proxmox"
    ):
        self.username = username
        self.root_password = root_password
        self.vm_ip = vm_ip
        self.valid_node = valid_node
        self.valid_id = ""
        self.vm_type = vm_type

def get_api_node():
    '''Picks a random node and tries to access /api2/json/version
       Will repeat until one responds. Randomized in an attempt at
       lazy load balancing.
       Returns List, 0 is ip, 1 is type.'''
       
    nodes = system_config['proxmox_nodes']['nodes']
    
    if not system_config['proxmox_nodes']['check_nodes']:
        return choice(nodes)
    
    while len(nodes) != 0:
        selected_node = choice(nodes)
        try:
            response = get(url=f'https://{selected_node}:8006/api2/json/version', headers=headers, verify=system_config['proxmox_nodes']['verify_ssl'])
            if response.status_code == 200:
                #API node send's a response, use it
                return selected_node
            nodes.remove(selected_node)
        except:
            pass
    return ""

def async_vm_creation():
    global vm_creation_queue, ready_for_vm_creation, status, qentry
    while True:
        if not vm_creation_queue.empty() and ready_for_vm_creation:
            ready_for_vm_creation = False
            qentry = vm_creation_queue.get()
            username = qentry.username
            root_password = qentry.root_password
            valid_node = qentry.valid_node
            valid_id = get_endpoint("/api2/extjs/cluster/nextid")
            qentry.valid_id = valid_id
            print(
                f"creating {qentry.vm_type} for {username} password: {root_password}, on {valid_node} with id {valid_id}"
            )
            data = system_config['vm-provision-options'][qentry.vm_type]
            vm_data = {}
            vm_data['name'] = username + "-" + qentry.vm_type
            
            if "template" in data and data['template']:
                vm_data['newid'] = valid_id
                vm_data['pool'] = data['pool']
                vm_data['target'] = valid_node
                vm_data['full'] = data['full']
                create_vm_from_template(vm_data, data['node'], data['vmid'])
                Thread(target=add_tags_to_template, kwargs={"vm_data": vm_data, 'username': username}).start()
            else:
                vm_data['node'] = valid_node
                vm_data['vmid'] = valid_id
                vm_data['cores'] = data['cores']
                vm_data['memory'] = data['memory']
                vm_data['agent'] = data['agent']
                vm_data['cpu'] = data['cpu']

                for i in range(0, len(data['networks'])):
                    vm_data['net' + str(i)] = data['networks'][i]

                vm_data['scsi0'] = f"{data['storage_location']}:{data['storage']},iothread=on"
                vm_data['start'] = data['start']
                vm_data['ide2'] = f"{data['iso_location']}:iso/{data['iso']},media=cdrom"
                vm_data['tags'] = username
                vm_data['pool'] = data['pool']
                create_vm(data=vm_data, node=valid_node, verifySSL=verify_ssl)  # Proxmox VM creation

            #groups = get_endpoint(endpoint="/api2/json/access/groups")
            create_group = post_endpoint(endpoint="/api2/extjs/access/groups", data={"groupid": valid_id, "comment": ""}) 
            add_vm_to_group = put_endpoint(endpoint="/api2/extjs/access/acl", data={"path": f"/vms/{valid_id}", "groups": valid_id, "roles": system_config['proxmox_nodes']['user_group'], "propagate": 1})
            #domains = get_endpoint(endpoint="/api2/json/access/domains")
            
            users = get_endpoint("/api2/json/access/users?full=1")
            for user in users:
                if user['userid'].split("@")[0] == username:
                    print(f"adding {user['userid']} to vm {valid_id} because equals username {username}")
                    groups = user['groups'].split(",")
                    groups.append(str(valid_id))
                    groups = ','.join(groups)
                    realm = user['userid'].split("@")[1]
                    add_user_to_group = put_endpoint(endpoint=f"/api2/extjs/access/users/{user['userid']}", data={"groups": groups}) 
            
            if 'needs_postinst' not in data or data['needs_postinst'] == False:
                ready_for_vm_creation = True
                print("created vm, no need to wait for automatic vm creation, ready for vm creation again")
        sleep(10)

def add_tags_to_template(vm_data: dict, username: str):
    sleep(100)
    r = put_endpoint(f"/api2/extjs/nodes/{vm_data['target']}/qemu/{vm_data['newid']}/config", {'tags': username})
    print(r)

def create_vm(data: dict, node: str, verifySSL: bool = verify_ssl) -> dict:
    endpoint = f"/api2/json/nodes/{node}/qemu"
    data['ostype'] = "l26"
    data['scsihw'] = 'virtio-scsi-single'
    data['sockets'] = 1
    return post_endpoint(endpoint=endpoint, data=data, verifySSL=verifySSL)

def create_vm_from_template(data:dict, node: str, vmid: str) -> dict:
    #  /api2/json/nodes/{node}/qemu/{vmid}/clone
    # /api2/extjs/nodes/{node}/qemu/{vmid}/clone
    endpoint = f"/api2/extjs/nodes/{node}/qemu/{vmid}/clone"
    r = post_endpoint(endpoint, data, {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"})
    
    return r

def recieve_postinst_ip():
    global qentry
    r = get_endpoint(endpoint=f"/api2/json/nodes/{qentry.valid_node}/qemu/{qentry.valid_id}/config")
    
    data={
        "net0": r["net0"].replace(str(system_config['vm-provision-options']['proxmox']['provision_vlan']), str(system_config['vm-provision-options']['proxmox']['user_vlan'])),
        "net1": r["net1"].replace("link_down=1", "link_down=0")
        }
    data['agent'] = 1
    print(f"Reconnecting Promxox management interface for {qentry.valid_id}", end="")
    print(data)
    r = put_endpoint(endpoint=f"/api2/json/nodes/{qentry.valid_node}/qemu/{qentry.valid_id}/config", data=data )
    print(r)


def get_endpoint(endpoint:str, verifySSL:bool=verify_ssl) -> str:
    ip = get_api_node()
    if ip == "":
        return {"result": "cannot connect to Proxmox"}
    r = get(
        url=f"https://{ip}:8006{endpoint}", verify=verifySSL, headers=headers
    )
    return r.json()["data"]


def post_endpoint(
    endpoint: str, data:dict, additional_headers={}, verifySSL=verify_ssl
) -> dict:
    ip = get_api_node()
    if ip == "":
        return {"result": "cannot connect to Proxmox"}
    
    post_headers = headers
    for key in additional_headers:
        post_headers[key] = additional_headers[key]
    r = post(
        url=f"https://{ip}:8006{endpoint}",
        data=data,
        headers=post_headers,
        verify=verifySSL,
    )
    r = r.json()["data"]
    return r


def put_endpoint(
    endpoint: str, data: dict, verifySSL=verify_ssl
) -> dict:
    ip = get_api_node()
    if ip == "":
        return {"result": "cannot connect to Proxmox"}
    r = put(
        url=f"https://{ip}:8006{endpoint}",
        data=data,
        headers=headers,
        verify=verifySSL,
    )
    #print(r)
    return r.json()


def create_ticket():
    global headers, ticket
    USERNAME = system_config['proxmox_nodes']['username']
    PASSWORD = system_config['proxmox_nodes']['password']
    endpoint = "/api2/json/access/ticket"
    data = {"username": f"{USERNAME}", "password": f"{PASSWORD}"}
    result = post_endpoint(endpoint=endpoint, data=data)
    try:
        headers["Cookie"] = f"PVEAuthCookie={result['ticket']}"
        headers['CSRFPreventionToken'] = result['CSRFPreventionToken']
        ticket = result['ticket']
    except TypeError:
        print("could not create ticket. Possible incorrect credentials")
        exit(0)


def refresh_ticket():
    global headers, ticket
    USERNAME = system_config['proxmox_nodes']['username']
    PASSWORD = system_config['proxmox_nodes']['password']
    endpoint = "/api2/json/access/ticket"
    data = {"username": f"{USERNAME}", "password": f"{ticket}"}

    result = post_endpoint(endpoint=endpoint, data=data)
    try:
        headers['Cookie'] = f"PVEAuthCookie={result['ticket']}"
        headers['CSRFPreventionToken'] = result["CSRFPreventionToken"]
        ticket = result["ticket"]
    except TypeError:
        print("could not create ticket. Possible incorrect credentials")
        exit(0)

def get_status() -> dict:
    endpoint = "/api2/json/cluster/resources"
    return get_endpoint(endpoint=endpoint)


def async_status():
    global status
    counter = 0
    while True:
        sleep(10)
        status = get_status()
        if system_config['proxmox_nodes']['authentication_type'] == "credentials":
            counter += 1
            if counter > 700:  # 7020 seconds
                counter = 0
                refresh_ticket() # tickets last two hours
        


def get_user_vms(username: str) -> dict:
    global status
    returnDict = {}
    for entry in range(0, len(status)):
        if "tags" in status[entry] and username in status[entry]["tags"].split(";"):
            if "ip" not in status[entry] and "vmid" in status[entry]:
                if "qemu" in status[entry]["id"]:
                    status[entry]["ip"] = get_interface_ip(
                        status[entry]["node"], str(status[entry]["vmid"])
                    )
                else:
                    status[entry]["ip"] = ""
            # lines that are commented is data which is not removed
            # status[entry].pop("name", None) # hostname of the vm
            status[entry].pop("diskread", None)
            status[entry].pop("disk", None)
            status[entry].pop("maxcpu", None)
            status[entry].pop("maxdisk", None)
            status[entry].pop("type", None)
            # status[entry].pop("node", None) # used to identify which node a VM is on when submitting a request from the GUI
            # status[entry].pop("tags", None) # used to identify access in the GUI
            status[entry].pop("template", None)
            status[entry].pop("diskwrite", None)
            # status[entry].pop("id", None) # includes the vm type, lxc/qemu. ex: qemu/1000
            status[entry].pop("vmid", None)  # just the vmid number. ex: 1000
            status[entry].pop("pool", None)
            returnDict[entry] = status[entry]

    # print(returnDict)
    return returnDict

def get_interface_ip(node: str, vmid: str) -> str:
    endpoint = f"/api2/json/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
    able_to_get_endpoint = False
    for _ in range(0, 3):
        try:
            r = get_endpoint(endpoint=endpoint)
            sleep(0.1)
            break
        except:
            pass
    if not able_to_get_endpoint:
        return ""
    
    r = r["result"]
    for interface in r:
        if interface["name"] == "vmbr0":
            for ip_type in range(0, len(interface["ip-addresses"])):
                if interface["ip-addresses"][ip_type]["ip-address-type"] == "ipv4":
                    return interface["ip-addresses"][ip_type]["ip-address"]


def does_have_personal_vm_created(vm_type, username: str) -> bool:
    for entry in status:
        if "node" in entry and "name" in entry:
            if username + "-" + vm_type == entry["name"]:
                return True
    return False


def send_answer_toml():
    global qentry, ready_for_vm_creation
    username = qentry.username
    root_password = qentry.root_password

    if username == "" or root_password == "" or ready_for_vm_creation:
        return {"status": "not expecting VM"}
    data = system_config['vm-provision-options'][qentry.vm_type]
    ready_for_vm_creation = True
    return (
        answer_file.replace("{{ username }}", username)
        .replace("{{ password }}", root_password)
        .replace("{{ lvm_max_root }}", str(data['lvm_max_root']))
        .replace("{{ proxmox_webapp_url }}", data['proxmox_webapp_url'])
        .replace(
            "{{ proxmox_webapp_fingerprint }}", data['proxmox_webapp_fingerprint'],
        )
    )


def send_first_boot_get():
    vm_string = ""
    vm_id = 100
    for image in system_config['vm-provision-options']['proxmox']['images']:
        data = system_config['vm-provision-options']['proxmox']['images'][image]
        vm_string += f'wget {data['image_url']} '
        if not data['image_url_verifyssl']:
            vm_string += "--no-check-certificate"
        vm_string += "\n"

        vm_string += f'qm create {vm_id} '
        vm_string += f'--cdrom {data['iso_location']}:iso/{data['iso']} '
        vm_string += f'--name {image} '
        vm_string += f'--numa {data['numa']} '
        vm_string += f'--ostype l26 '
        vm_string += f'--cpu cputype={data['cpu']} '
        vm_string += f'--cores {data['cores']} '
        vm_string += f'--memory {data['memory']} '

        network_num=0
        for net in data['networks']:
            vm_string += f'--net{network_num} {net} '
            network_num += 1
        #vm_string += f'--bootdisk scsi0,ide0 '
        vm_string += f'--scsihw virtio-scsi-pci '
        vm_string += f'--scsi0 file={data['storage_location']}:{data['storage']} '
        vm_string += f'--balloon {data['balloon']} '
        vm_string += f'--bios {data['bios']} '
        vm_string += f'--start {data['start']} '
        vm_string += "\n\n"

        vm_id += 1

    return first_boot_file.replace("#{{replace_with_vms}}", vm_string)


def does_user_own_vm(
    vmid: str, username: str
) -> tuple:  # returns the vm name if the user owns it, otherwise ""
    for entry in range(0, len(status)):
        if vmid == status[entry]["id"].split("/")[1] and username == status[entry]["name"].rsplit("-", 1)[0]:
            return status[entry]["name"], status[entry]["tags"], status[entry]["node"]
        elif vmid == status[entry]["id"].split("/")[1] and username in status[entry]["tags"].split(";"):
            return "", status[entry]["tags"], status[entry]["node"]
    return "", "", ""


def set_vm_power(node: str, vmid: str, power_value: str):
    endpoint = f"/api2/json/nodes/{node}/{vmid}/status/{power_value}"
    #print(endpoint)
    data = {}
    post_endpoint(endpoint=endpoint, data=data)

if system_config['proxmox_nodes']['authentication_type'] == "credentials":
    headers = {"CSRFPreventionToken": "", "Cookie": "PVEAuthCookie="}
    create_ticket()
    if headers["Cookie"] == "PVEAuthCookie=":
        print("Could not get ticket! Exiting")
        exit(1)
else:
    API_TOKEN = system_config['proxmox_nodes']['token']
    headers = {"Authorization" : f"PVEAPIToken={API_TOKEN}"}

if __name__ == "__main__":
    # endpoint = "/api2/extjs/nodes/proxmox2/lxc/300/config"
    # data = {"tags": "dtomo001"}
    # print(put_endpoint(endpoint=endpoint, data=data))
    # node = "pve2"
    # vmid = "1000"
    # print(get_user_vms("dtomo001"))
    # create_vm("dtomo001", "pve2", 2004)
    # print(get_interface_ip("pve2", "4000"))
    # vm_creation_queue.put(QueueEntry("dtomo001", "password"))
    """"""
    #print(create_fw())
    status = get_status()
    #print(status)
    r = put_endpoint(f"/api2/extjs/nodes/cybprodserv4-5/qemu/4028/config", {'tags': 'dtomo001'})
    print(r)
    exit(0)
    r = get_endpoint(endpoint="/api2/json/nodes/proxmox2/qemu/2001/config", headers=headers)
    #print(r)
    print(r["net1"])
    if "link_down=1" in r["net1"]:
        r = put_endpoint(endpoint="/api2/json/nodes/proxmox2/qemu/2001/config", data={"net1": r["net1"].replace("link_down=1", "link_down=0")})
    else:
        r = put_endpoint(endpoint="/api2/json/nodes/proxmox2/qemu/2001/config", data={"net1": r["net1"].replace("link_down=0", "link_down=1")})
    print(r)
# print(get_interface_ip(node=node, vmid=vmid))
else:
    status = get_status()
    Thread(target=async_status).start()
    Thread(target=async_vm_creation).start()
    """"""
