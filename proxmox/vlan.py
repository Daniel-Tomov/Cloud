from flask import (
    Flask,
    session,
    request,
)
import re
import psycopg2
from proxmox import does_user_own_vm, get_api_node, get_endpoint, put_endpoint
from threading import Thread
from random import choice
class VLAN:
    def __init__(self, app:Flask, system_config:dict) -> None:
        self.app = app
        self.system_config = system_config
        self.register_routes()
        
        self.database=self.system_config['cache_database']['database']
        self.user=self.system_config['cache_database']['user']
        self.password=self.system_config['cache_database']['password']
        self.host=self.system_config['cache_database']['host']
        self.port=self.system_config['cache_database']['port']
        self.sslmode=self.system_config['cache_database']['sslmode']
        
        self.create_tables()
    
    def connect(self):
        connection = psycopg2.connect(
            database=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            sslmode=self.sslmode
        )
        return connection, connection.cursor()

    def create_tables(self):
        if self.host == "":
            return
        connection, cursor = self.connect()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS vlans (username VARCHAR(32) UNIQUE, tags VARCHAR(65535));"
        )
        cursor.execute(f"SELECT * FROM vlans WHERE username = 'available-vlans';")
        result = cursor.fetchall()
        
        if result == []:
            available = ';'.join([str(i) for i in range(self.system_config['proxmox_nodes']['vlans']['min'], self.system_config['proxmox_nodes']['vlans']['max'] + 1)])
            self.add_vlan('available-vlans', available)

        
        connection.commit()
        connection.close()
        
    def get_vlans(self, username):
        connection, cursor = self.connect()
        cursor.execute(f"SELECT * FROM vlans WHERE username = %s", (username,))
        result = cursor.fetchall()
        if result == []:
            cursor.execute(
                f"INSERT INTO vlans (username, tags) VALUES (%s, %s)",
                (username, "")
            )
            connection.commit()
            connection.close()
            return ""
        
        connection.commit()
        connection.close()
        
        if result == None:
            return ""
        return result[0][1]
    
    def access_to_vlan(self, username, vlan) -> bool:
        result = self.get_vlans(username).split(";")
        if len(result) > 10 and vlan not in result:
            print("too many vlans")
            return False
        if vlan in result:
            return True
        result = self.get_vlans('available-vlans').split(";")
        if vlan in result:
            self.add_vlan(username, vlan)
            self.remove_vlan('available-vlans', vlan)
            return True
        return False
        
        
    def add_vlan(self, username, vlan):
        print(f'adding vlan {vlan} for {username}')
        Thread(target=self.async_add_vlan, kwargs={"username": username, "vlan": vlan}).start()
    
    def async_add_vlan(self, username, vlan):
        vlans = self.get_vlans(username).split(";")
        vlans.append(vlan)
        vlans.sort()
        vlans = ';'.join(vlans)
        self.async_add_vlans(username, vlans)
        
    def add_vlans(self, username, vlans):
        Thread(target=self.async_add_vlans, kwargs={"username": username, "vlans": vlans}).start()
        
    def async_add_vlans(self, username, vlans):
        connection, cursor = self.connect()
        cursor.execute(
            f"UPDATE vlans SET tags = %s WHERE username = %s", (vlans, username)
        )
        connection.commit()
        connection.close()
        
    def remove_vlan(self, username, vlan):
        Thread(target=self.async_remove_vlan, kwargs={"username": username, "vlan": vlan}).start()
        
    def async_remove_vlan(self, username, vlan):
        vlans = self.get_vlans(username).split(";")
        vlans.remove(vlan)
        if "" in vlans:
            vlans.remove("")
        vlans = ';'.join(vlans)
        
        
        connection, cursor = self.connect()
        cursor.execute(
            f"UPDATE vlans SET tags = %s WHERE username = %s", (vlans, username)
        )
        connection.commit()
        connection.close()
        
        
        
        
    def register_routes(self):
        @self.app.route("/vlan/<string:username>/<string:vmid>", methods=["GET", "POST"])
        def get_vmid_vlans(username:str, vmid: str) -> dict:
            name, tags, node = does_user_own_vm(vmid, username)
            if username not in tags.split(";"):
                return {"result": "You do not own this VM!"}
            r = get_endpoint(f"/api2/json/nodes/{node}/qemu/{vmid}/pending")
            if request.method == 'GET':
                result = {'nets': {}}
                for i in r:
                    if "net" in i['key']:
                        if 'tag' not in i['value']:
                            i['value'] += ",tag=1"
                        if 'link_down' not in i['value']:
                            i['value'] += ',link_down=0'
                        result['nets'][i['key']] = i['value']

                result['name'] = name
                result['node'] = node

                return result
            elif request.method == "POST":
                r = get_endpoint(f"/api2/json/nodes/{node}/qemu/{vmid}/pending")
                digest = ""
                for i in r:
                    if i['key'] == "digest":
                        digest = i['value']
                if digest == "":
                    return {'result': 'invalid'}
                if 'data' not in request.json:
                    return {'result': 'data not in request'}
                if 'tag' not in request.json['data']:
                    return {'result': 'tag not in request'}
                if 'link_down' not in request.json['data']:
                    return {'result': 'link_down not in request'}
                
                tag = request.json['data'].split("tag=")[1].split(",")[0]
                
                if not re.search(self.system_config['proxmox_nodes']['vlans']['regex'], tag):
                    return {'result': 'invalid tag'}
                if not re.search('0|1', request.json['data'].split("link_down=")[1]):
                    return {'result': 'invalid link_down value'}
                
                if tag in self.system_config['proxmox_nodes']['vlans']['special']:
                    pass
                else:
                    if not self.access_to_vlan(username, tag):
                        return {"result": "No access to that vlan"}
                r = put_endpoint(f'/api2/extjs/nodes/{node}/qemu/{vmid}/config', data={'digest': digest, request.json['data'].split("=", 1)[0]: request.json['data'].split("=", 1)[1]})
                return r
            return {'result': 'invalid'}
        
        @self.app.route("/vlan/<string:username>/<string:vmid>/<string:add_or_remove>", methods=["GET", 'POST'])
        def modify_adapters(username:str, vmid:str, add_or_remove:str):
            name, tags, node = does_user_own_vm(vmid, username)
            if username != name.rsplit("-")[0]:
                return {"result": "You do not own this VM!"}
            
            #net3 = virtio,bridge=vmbr1,tag=1,firewall=1

            if add_or_remove == 'add':
                r = get_endpoint(f"/api2/json/nodes/{node}/qemu/{vmid}/pending")
                digest = ""
                for i in r:
                    if i['key'] == "digest":
                        digest = i['value']
                    
                if digest == "":
                    return {'result': 'invalid'}
                networks = []
                for i in r:
                    if 'net' in i['key']:
                        networks.append(i['key'])
                        
                valid_net_id = 11
                for i in range(0,10):
                    if f'net{i}' not in networks:
                        valid_net_id = i
                        break
                available_vlans = self.get_vlans(username).split(";")
                if len(available_vlans) == 0:
                    self.access_to_vlan(username, choice(self.get_vlans('available-vlans').split(";")))
                    available_vlans = self.get_vlans(username).split(";")
                
                r = put_endpoint(f'/api2/extjs/nodes/{node}/qemu/{vmid}/config', data={'digest': digest, f'net{valid_net_id}': f"virtio,bridge={self.system_config['proxmox_nodes']['vlans']['vm_bridge']},tag={choice(available_vlans)},firewall=0"})
                return r
            elif add_or_remove == "remove":
                r = put_endpoint(f"/api2/extjs/nodes/{node}/qemu/{vmid}/config", data=request.json)
                return r
            return {"result": "failed to add"}
                
                
            # https://10.60.76.27:8006/api2/extjs/nodes/cybprodserv2-4/qemu/4007/config