from yaml import safe_load
import psycopg2


class Fix:
    def __init__(self):
        
        with open('../../vm-options.yaml', 'r') as config:
            self.system_config = safe_load(config)
        
        self.database=self.system_config['cache_database']['database']
        self.user=self.system_config['cache_database']['user']
        self.password=self.system_config['cache_database']['password']
        self.host=self.system_config['cache_database']['host']
        self.port=self.system_config['cache_database']['port']
        self.sslmode=self.system_config['cache_database']['sslmode']
        
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
    
    def fix_global(self):
        connection, cursor = self.connect()
        cursor.execute(f"SELECT * FROM vlans WHERE username != 'available-vlans';")
        result = cursor.fetchall()
        
        for user in result:
            cursor.execute(f"SELECT * FROM vlans WHERE username = 'available-vlans';")
            available = cursor.fetchall()[0][1].split(";")
            print(f'{available=}')
            for tag in user[1].split(";"):
                if tag != "":
                    print(tag)
                    if tag in available:
                        available.remove(tag)
            available.sort()
            if "" in available:
                available.remove("")
            available = ';'.join(available)
            cursor.execute(
                f"UPDATE vlans SET tags = %s WHERE username = %s", (available, 'available-vlans')
            )
        print(result)
        
        connection.commit()
        connection.close()
        return ""
    
    def fix_user(self, username):
        connection, cursor = self.connect()
        cursor.execute(f"SELECT * FROM vlans WHERE username = %s;", (username,))
        result = cursor.fetchall()[0][1]
        
        tags = result.split(";")
        if "" in tags:
            tags.remove("")
        tags = ";".join(tags)
        print(tags)
        cursor.execute(
            f"UPDATE vlans SET tags = %s WHERE username = %s", (tags, username)
        )
        connection.commit()
        connection.close()
        

#Fix().fix_global()
Fix().fix_user('wholb001')