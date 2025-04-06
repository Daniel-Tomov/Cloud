#!/bin/bash

OUTPUT_FOLDER=./configs
USER=root
node1=10.10.10.11
node2=10.10.10.12
node3=10.10.10.13
vip=10.10.10.10

keepalived_password=changeme
keepalived_router_id=1


#mkdir -p $OUTPUT_FOLDER
#rm -Rf $OUTPUT_FOLDER/*
cd $OUTPUT_FOLDER





function install {
    LOCALIP=$1
    LOCALUSER=$2
    LOCALNODENAME=$3
    echo "$LOCALIP $LOCALUSER $LOCALNODENAME"
    sleep 1
    #ssh $LOCALUSER@$LOCALIP sudo apt update
    #ssh $LOCALUSER@$LOCALIP sudo apt install -y postgresql-common tmux net-tools
    #ssh $LOCALUSER@$LOCALIP sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
    #ssh $LOCALUSER@$LOCALIP sudo apt update
    #ssh $LOCALUSER@$LOCALIP sudo apt install -y postgresql postgresql-contrib wget curl patroni acl keepalived haproxy
    #ssh $LOCALUSER@$LOCALIP sudo systemctl stop postgresql
    #ssh $LOCALUSER@$LOCALIP sudo systemctl disable postgresql
    #ssh $LOCALUSER@$LOCALIP wget https://github.com/etcd-io/etcd/releases/download/v3.5.17/etcd-v3.5.17-linux-amd64.tar.gz
    #ssh $LOCALUSER@$LOCALIP tar xvf etcd-v3.5.17-linux-amd64.tar.gz
    #ssh $LOCALUSER@$LOCALIP rm etcd-v3.5.17-linux-amd64.tar.gz*
    #ssh $LOCALUSER@$LOCALIP mv etcd-v3.5.17-linux-amd64 etcd
    #ssh $LOCALUSER@$LOCALIP sudo mv etcd/etcd* /usr/local/bin/
    #ssh $LOCALUSER@$LOCALIP rm -Rf etcd
    #ssh $LOCALUSER@$LOCALIP sudo useradd --system --home /var/lib/etcd --shell /bin/false etcd
    #ssh $LOCALUSER@$LOCALIP sudo mkdir -p /etc/etcd
    #ssh $LOCALUSER@$LOCALIP sudo mkdir -p /etc/etcd/ssl

    openssl genrsa -out etcd-$LOCALNODENAME.key 2048

cat > etcd-$LOCALNODENAME.cnf <<EOF
[ req ]
distinguished_name = req_distinguished_name
req_extensions = v3_req
[ req_distinguished_name ]
[ v3_req ]
subjectAltName = @alt_names
[ alt_names ]
IP.1 = $LOCALIP
IP.2 = 127.0.0.1
EOF
    openssl req -new -key etcd-$LOCALNODENAME.key -out etcd-$LOCALNODENAME.csr \
    -subj "/C=US/ST=YourState/L=YourCity/O=YourOrganization/OU=YourUnit/CN=etcd-$LOCALNODENAME" \
    -config etcd-$LOCALNODENAME.cnf
    openssl x509 -req -in etcd-$LOCALNODENAME.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out etcd-$LOCALNODENAME.crt -days 7300 -sha256 -extensions v3_req -extfile etcd-$LOCALNODENAME.cnf
    openssl x509 -in etcd-$LOCALNODENAME.crt -text -noout | grep -A1 "Subject Alternative Name"

    scp ca.crt etcd-$LOCALNODENAME.crt etcd-$LOCALNODENAME.key $LOCALUSER@$LOCALIP:/tmp/

    ssh $LOCALUSER@$LOCALIP sudo mkdir -p /etc/etcd/ssl
    ssh $LOCALUSER@$LOCALIP sudo rm -Rf /etc/etcd/ssl
    ssh $LOCALUSER@$LOCALIP sudo mkdir -p /etc/etcd/ssl
    ssh $LOCALUSER@$LOCALIP sudo mv /tmp/etcd-node*.crt /etc/etcd/ssl/
    ssh $LOCALUSER@$LOCALIP sudo mv /tmp/etcd-node*.key /etc/etcd/ssl/
    ssh $LOCALUSER@$LOCALIP sudo mv /tmp/ca.crt /etc/etcd/ssl/
    ssh $LOCALUSER@$LOCALIP sudo chown -R etcd:etcd /etc/etcd/
    ssh $LOCALUSER@$LOCALIP sudo chmod 600 /etc/etcd/ssl/etcd-node*.key
    ssh $LOCALUSER@$LOCALIP sudo chmod 644 /etc/etcd/ssl/etcd-node*.crt /etc/etcd/ssl/ca.crt


    cat ../etcd.env | sed "s/node1/$node1/g" | sed "s/node2/$node2/g" | sed "s/node3/$node3/g" | sed "s/nodename/$LOCALNODENAME/g" | sed "s/ip/$LOCALIP/g" > etcd-$LOCALNODENAME.env
    scp etcd-$LOCALNODENAME.env $LOCALUSER@$LOCALIP:/etc/etcd/etcd.env
    scp ../etcd.service $LOCALUSER@$LOCALIP:/etc/systemd/system/etcd.service
    ssh $LOCALUSER@$LOCALIP sudo mkdir -p /var/lib/etcd 
    ssh $LOCALUSER@$LOCALIP sudo chown -R etcd:etcd /var/lib/etcd
    ssh $LOCALUSER@$LOCALIP sudo usermod -aG etcd $USER

    ssh $LOCALUSER@$LOCALIP sudo mkdir -p /var/lib/postgresql/data
    ssh $LOCALUSER@$LOCALIP sudo mkdir -p /var/lib/postgresql/ssl

    scp server.crt server.key server.req $LOCALUSER@$LOCALIP:/tmp
    ssh $LOCALUSER@$LOCALIP mv /tmp/server.crt /var/lib/postgresql/ssl
    ssh $LOCALUSER@$LOCALIP mv /tmp/server.key /var/lib/postgresql/ssl
    ssh $LOCALUSER@$LOCALIP mv /tmp/server.req /var/lib/postgresql/ssl
    ssh $LOCALUSER@$LOCALIP sudo chmod 600 /var/lib/postgresql/ssl/server.key
    ssh $LOCALUSER@$LOCALIP sudo chmod 644 /var/lib/postgresql/ssl/server.crt
    ssh $LOCALUSER@$LOCALIP sudo chmod 600 /var/lib/postgresql/ssl/server.req
    ssh $LOCALUSER@$LOCALIP sudo chown postgres:postgres /var/lib/postgresql/data
    ssh $LOCALUSER@$LOCALIP sudo chown postgres:postgres /var/lib/postgresql/ssl/server.*

    ssh $LOCALUSER@$LOCALIP sudo setfacl -m u:postgres:r /etc/etcd/ssl/ca.crt
    ssh $LOCALUSER@$LOCALIP sudo setfacl -m u:postgres:r /etc/etcd/ssl/etcd-$LOCALNODENAME.crt
    ssh $LOCALUSER@$LOCALIP sudo setfacl -m u:postgres:r /etc/etcd/ssl/etcd-$LOCALNODENAME.key

    ssh $LOCALUSER@$LOCALIP sudo mkdir -p /etc/patroni/
    cat ../patroni.yml | sed "s/node1/$node1/g" | sed "s/node2/$node2/g" | sed "s/node3/$node3/g" | sed "s/nodename/$LOCALNODENAME/g" | sed "s/ip/$LOCALIP/g" > patroni-$LOCALNODENAME.yml
    scp patroni-$LOCALNODENAME.yml $LOCALUSER@$LOCALIP:/etc/patroni/config.yml

    cat server.crt server.key > server.pem
    scp server.pem $LOCALUSER@$LOCALIP:/var/lib/postgresql/ssl/server.pem
    ssh $LOCALUSER@$LOCALIP sudo chown postgres:postgres /var/lib/postgresql/ssl/server.pem
    ssh $LOCALUSER@$LOCALIP sudo chmod 600 /var/lib/postgresql/ssl/server.pem
    

    cat ../haproxy.cfg | sed "s/node1/$node1/g" | sed "s/node2/$node2/g" | sed "s/node3/$node3/g" | sed "s/nodename/$LOCALNODENAME/g" | sed "s/ip/$LOCALIP/g" > haproxy-$LOCALNODENAME.cfg
    scp haproxy-$LOCALNODENAME.cfg $LOCALUSER@$LOCALIP:/etc/haproxy/haproxy-tmp.cfg
    #ssh $LOCALUSER@$LOCALIP cat /etc/haproxy/haproxy-tmp.cfg >> /etc/haproxy/haproxy.cfg
    

    cat ../haproxy-keepalived.conf | sed "s/_password_/$keepalived_password/g" | sed "s/_routerid_/$keepalived_router_id/g" | sed "s/vip/$vip/g" > haproxy-keepalived.conf
    scp haproxy-keepalived.conf $LOCALUSER@$LOCALIP:/etc/keepalived/keepalived.conf
    scp ../check_haproxy.sh $LOCALUSER@$LOCALIP:/etc/keepalived/check_haproxy.sh
    ssh $LOCALUSER@$LOCALIP sudo useradd -r -s /bin/false keepalived_script
    ssh $LOCALUSER@$LOCALIP sudo chmod +x /etc/keepalived/check_haproxy.sh
    ssh $LOCALUSER@$LOCALIP sudo chown keepalived_script:keepalived_script /etc/keepalived/check_haproxy.sh
    ssh $LOCALUSER@$LOCALIP sudo chmod 700 /etc/keepalived/check_haproxy.sh

}

function restart {
    LOCALIP=$1
    LOCALUSER=$2
    LOCALNODENAME=$3
    echo "$LOCALIP $LOCALUSER $LOCALNODENAME"
    sleep 10
    nohup bash -c "sosh $LOCALUSER@$LOCALIP bash -c 'nohup sudo systemctl restart patroni > /dev/null 2>&1&' >/dev/null 2>&1&"
    ssh $LOCALUSER@$LOCALIP sudo systemctl reload haproxy
    ssh $LOCALUSER@$LOCALIP sudo systemctl restart keepalived
    ssh $LOCALUSER@$LOCALIP sudo systemctl daemon-reload
    ssh $LOCALUSER@$LOCALIP sudo systemctl enable etcd
    ssh $LOCALUSER@$LOCALIP sudo systemctl start etcd
}


#sudo apt install openssl
#openssl genrsa -out ca.key 2048
#openssl req -x509 -new -nodes -key ca.key -subj "/CN=etcd-ca" -days 7300 -out ca.crt

#openssl genrsa -out server.key 2048
#openssl req -new -key server.key -out server.req
#openssl req -x509 -key server.key -in server.req -out server.crt -days 7300 
#chmod 600 server.key

#install $node1 $USER 'node1'
install $node2 $USER 'node2'
#install $node3 $USER 'node3'

#sudo mv server.crt server.key server.req /var/lib/postgresql/ssl