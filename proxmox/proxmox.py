from requests import get, post, put
from dotenv import load_dotenv
from os import getenv
from threading import Thread
from time import sleep
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from queue import Queue


load_dotenv()
USERNAME = getenv("PVE_USER")
PASSWORD = getenv("PVE_PASS")
API_TOKEN = getenv("PVE_TOKEN")
URL = getenv("PVE_URL")
verify_ssl = getenv("verify_ssl_pve", "False") == "True"
if not verify_ssl:
    disable_warnings(InsecureRequestWarning)

if API_TOKEN == None or API_TOKEN == "":
    headers = {"CSRFPreventionToken": "", "Cookie": "PVEAuthCookie="}
else:
    headers = {"Authorization" : f"PVEAPIToken={API_TOKEN}"}


vm_creation_queue = Queue()
ready_for_vm_creation = True


first_boot_file = open("first-boot.sh").read()
answer_file = open("answer.toml").read()


class QueueEntry:
    def __init__(
        self,
        midas: str = "bigblue001",
        root_password: str = "password",
        vm_ip: str = "",
        valid_node: str = "",
    ):
        self.midas = midas
        self.root_password = root_password
        self.vm_ip = vm_ip
        self.valid_node = valid_node
        self.valid_id = ""


def async_vm_creation():
    global vm_creation_queue, ready_for_vm_creation, status, qentry
    while True:
        if not vm_creation_queue.empty() and ready_for_vm_creation:
            ready_for_vm_creation = False
            qentry = vm_creation_queue.get()
            midas = qentry.midas
            root_password = qentry.root_password
            valid_node = qentry.valid_node
            dictionary_of_ids = {}
            valid_id = 4000
            for entry in range(0, len(status)):
                if "node" in status[entry]:
                    id = status[entry]["id"].split("/")[1]
                    try:
                        dictionary_of_ids[int(id)] = "1"
                    except:
                        pass
            for location in range(4000, 999999999):
                try:
                    dictionary_of_ids[location]
                except:
                    valid_id = location
                    break
            qentry.valid_id = valid_id
            print(
                f"creating VM for {midas} password: {root_password}, on {valid_node} with id {valid_id}"
            )
            create_vm(
                name=midas,
                node=valid_node,
                vmid=valid_id,
                cores=getenv("PVE_CORES"),
                memory=getenv("PVE_MEMORY"),
                agent=1,
                net0=f"virtio,bridge={getenv('PVE_INTERFACE')},firewall=0,tag={getenv('PVE_VLAN')},link_down=0",
                net1=f"virtio,bridge={getenv('PVE_INTERFACE')},firewall=0,link_down=1,tag={getenv('FW_VLAN')}",
                scsi0=f"local-lvm:{getenv('PVE_GUEST_STORAGE')},iothread=on",
                start=1,
                ide2=f"local:iso/{getenv('proxmox_http_iso')},media=cdrom",
                tags=midas,
                ip=URL,
                verifySSL=False,
            )  # Proxmox VM creation
        sleep(10)


def create_vm(
    name: str,
    node: str,
    vmid: int,
    cores: int,
    memory: int,
    agent: int,
    net0: str,
    net1: str,
    scsi0: str,
    ide2: str,
    start: int = 0,
    net2: str = "",
    tags: str = "",
    ip: str = URL,
    verifySSL: bool = verify_ssl,
    headers: dict = headers,
) -> dict:
    endpoint = f"/api2/json/nodes/{node}/qemu"
    data = {
        "name": name,
        "vmid": vmid,
        "agent": agent,
        "boot": "order=scsi0;ide2",
        "bios": "seabios",
        "cpu": "host",
        "cores": cores,
        "sockets": 1,
        "memory": memory,
        "numa": 0,
        "net0": net0,
        "ostype": "l26",
        "scsi0": scsi0,
        "scsihw": "virtio-scsi-single",
        "start": start,
        "ide2": ide2,
        "tags": tags,
    }
    if net1 != "":
        data["net1"] = net1
    if net2 != "":
        data["net2"] = net2
    return post_endpoint(
        url=ip, endpoint=endpoint, data=data, headers=headers, verifySSL=verifySSL
    )


def recieve_postinst_ip(ip: str):
    global qentry
    if ip != qentry.vm_ip:
        print(
            f"toml and postinst ips do not match! using postinst if it is not empty. postinst: {ip}"
        )
    if ip == "":
        print("postinst ip was empty")
    else:
        qentry.vm_ip = ip


def get_endpoint(endpoint:str, url:str=URL, headers:dict=headers, verifySSL:bool=verify_ssl) -> str:
    r = get(
        url=f"https://{url}:8006{endpoint}", verify=verifySSL, headers=headers
    )
    return r.json()["data"]


def post_endpoint(
    endpoint: str, data: dict, url=URL, headers: dict = headers, verifySSL=verify_ssl
) -> dict:
    r = post(
        url=f"https://{url}:8006{endpoint}",
        data=data,
        headers=headers,
        verify=verifySSL,
    )
    r = r.json()["data"]
    return r


def put_endpoint(
    endpoint: str, data: dict, headers: dict = headers, url=URL, verifySSL=verify_ssl
) -> dict:
    r = put(
        url=f"https://{url}:8006{endpoint}",
        data=data,
        headers=headers,
        verify=verifySSL,
    )
    #print(r)
    return r.json()


def create_ticket():
    global headers, ticket
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

if API_TOKEN == "" or API_TOKEN == None:
    create_ticket()

def refresh_ticket():
    global headers, ticket
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


if API_TOKEN == "" and headers["Cookie"] == "PVEAuthCookie=":
    print("Could not get ticket! Exiting")
    exit(1)


def get_status() -> dict:
    endpoint = "/api2/json/cluster/resources"
    return get_endpoint(endpoint=endpoint)




def async_status():
    global status
    counter = 0
    while True:
        sleep(10)
        status = get_status()
        if API_TOKEN == "" or API_TOKEN == None:
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
            returnDict[entry] = status[entry]

    # print(returnDict)
    return returnDict


def get_interface_ip(node: str, vmid: str) -> str:
    endpoint = f"/api2/json/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
    r = get_endpoint(endpoint=endpoint)
    if r == None:
        return ""
    r = r["result"]
    for interface in r:
        if interface["name"] == "vmbr0":
            for ip_type in range(0, len(interface["ip-addresses"])):
                if interface["ip-addresses"][ip_type]["ip-address-type"] == "ipv4":
                    return interface["ip-addresses"][ip_type]["ip-address"]


def does_have_personal_vm_created(username: str) -> bool:
    for entry in status:
        if "node" in entry and "name" in entry:
            if username in entry["name"]:
                return True

    return False


def send_answer_toml():
    global qentry
    midas = qentry.midas
    root_password = qentry.root_password

    if midas == "" or root_password == "":
        return {"status": "not expecting VM"}
    return (
        answer_file.replace("{{ midas }}", midas)
        .replace("{{ password }}", root_password)
        .replace("{{ lvm_max_root }}", getenv("lvm_max_root"))
        .replace("{{ post_installation_url }}", getenv("proxmox_webapp_url") + '/postinst')
        .replace(
            "{{ post_installation_url_fingerprint }}",
            getenv("proxmox_webapp_fingerprint"),
        )
        .replace("{{ first_boot_script_url }}", getenv("proxmox_webapp_url") + '/first-boot.sh')
        .replace(
            "{{ first_boot_script_url_fingerprint }}",
            getenv("proxmox_webapp_fingerprint"),
        )
    )


def send_first_boot_get():
    return (
        first_boot_file.replace("{{ iso_img_domain }}", getenv("iso_img_domain"))
        .replace("{{ FW_IMAGE }}", getenv("FW_IMAGE"))
        .replace("{{ create_fw_url }}", getenv("proxmox_webapp_url") + "/create_fw")
        .replace("{{ ANTIX_IMAGE }}", getenv("ANTIX_IMAGE"))
    )


def create_fw():
    global qentry, ready_for_vm_creation
    ip = qentry.vm_ip
    midas = qentry.midas
    root_password = qentry.root_password
    if midas == "" or root_password == "":
        return {"status": "not expecting VM"}
    
    r = get_endpoint(endpoint=f"/api2/json/nodes/{qentry.valid_node}/qemu/{qentry.valid_id}/config")
    print("Reconnecting FW interface for ", end="")
    print(r["net1"])
    r = put_endpoint(endpoint=f"/api2/json/nodes/{qentry.valid_node}/qemu/{qentry.valid_id}/config", data={"net1": r["net1"].replace("link_down=1", "link_down=0")})
    print(r)
    
    if ip == None or ip == "":
        get_interface_ip(qentry.valid_node, qentry.valid_id)
    print(f"creating fw on {ip}")


    # Get ticket for the Guest Proxmox VM to create OPNsense Firewall VM
    student_headers = {"CSRFPreventionToken": "", "Cookie": "PVEAuthCookie="}
    endpoint = "/api2/json/access/ticket"
    data = {"username": "root@pam", "password": f"{root_password}"}
    result = post_endpoint(
        endpoint=endpoint, data=data, url=ip, headers=student_headers, verifySSL=False
    )
    student_headers["Cookie"] = f"PVEAuthCookie={result['ticket']}"
    student_headers["CSRFPreventionToken"] = result["CSRFPreventionToken"]
    r = create_vm(
        name="opnsense-firewall",
        node=midas,
        vmid=100,
        cores=2,
        memory=getenv("FW_MEMORY"),
        agent=0,
        net0="virtio,bridge=vmbr2,link_down=0",
        net1="virtio,bridge=vmbr1,link_down=0",
        net2="",
        scsi0=f"local-lvm:{getenv('FW_STORAGE')},iothread=on",
        ide2=f"local:iso/{getenv('FW_IMAGE')},media=cdrom",
        start=0,
        tags="",
        ip=ip,
        headers=student_headers,
    )
    print(f"created fw for {midas}")

    r = create_vm(
        name="antix",
        node=midas,
        vmid=101,
        cores=1,
        memory=getenv("ANTIX_MEMORY"),
        agent=0,
        net0="virtio,bridge=vmbr2,link_down=0",
        net1="",
        net2="",
        scsi0=f"local-lvm:{getenv('ANTIX_STORAGE')},iothread=on",
        ide2=f"local:iso/{getenv('ANTIX_IMAGE')},media=cdrom",
        start=0,
        tags="",
        ip=ip,
        headers=student_headers,
    )
    print(f"created antix for {midas}")

    # print(r)
    qentry = ""
    ready_for_vm_creation = True
    return {"result": "success"}


def does_user_own_vm(
    vmid: str, username: str
) -> str:  # returns the vm name if the user owns it, otherwise ""
    for entry in range(0, len(status)):
        if vmid == status[entry]["id"] and username in status[entry]["name"]:
            return status[entry]["name"], status[entry]["tags"]
    return "", ""


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
    print(status)
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
