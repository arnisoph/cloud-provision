#!/usr/bin/env python3

# ./create --token= --min=0 --max=0 --prefix=saltmaster --saltmaster
# ./create --token= --min=0 --max=0 --prefix=db --saltmaster_address=
# ./create --token= --min=0 --max=0 --prefix=fe --saltmaster_address=
# ./create --token= --min=1 --max=5 --prefix=mw --saltmaster_address= --image=centos-7-0-x64

import argparse
import digitalocean
from time import sleep
import paramiko
from rcontrol.core import SessionManager
from rcontrol.local import LocalSession
from rcontrol.ssh import SshSession, ssh_client
from collections import OrderedDict

node_names = {}


def sorted_dict(var):
    """
    Return a sorted dict as OrderedDict
    """
    ret = OrderedDict()
    for key in sorted(list(var.keys())):
        ret[key] = var[key]
    return ret


def install_salt(script_url, hostnames=None, username='root', password=None, port=22, master=False, master_address='127.0.0.1', image=None):
    def log(task, line):
        pass
        #print("%r -> : %s" % (task, line))

    with SessionManager() as sessions:
        sessions['local'] = LocalSession()
        for hostname in hostnames:
            try:
                sessions[hostname] = SshSession(ssh_client(hostname, username, password))
                sessions['local'].s_copy_file(script_url, sessions[hostname], '/var/tmp/bootstrap.sh')
            except TimeoutError as err:
                print('Timeout during SSH authentication ({}), trying one last time ({})'.format(err, hostname))
                sleep(10)
                sessions[hostname] = SshSession(ssh_client(hostname, username, password))
            except paramiko.ssh_exception.AuthenticationException as err:
                print('Failed to authenticate ({}), trying one last time ({})'.format(err, hostname))
                sleep(10)
                sessions[hostname] = SshSession(ssh_client(hostname, username, password))

        for hostname in hostnames:
            command = ('export DEBIAN_FRONTEND=noninteractive; ' +
                       'apt-get install -qy screen || yum install -y screen; ' +
                       'wget -q {} -O prepare.sh 2>&1 1>/tmp/prepare.log; '.format(script_url) +
                       'screen -dmS root bash /var/tmp/bootstrap.sh {} &> /tmp/vm-bootstrap.log'.format(master_address))
            print('Bootstrapping {} ({})'.format(node_names[hostname], hostname))
            sessions[hostname].execute(command, on_stderr=log, on_stdout=log)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--min',
                        action='store',
                        dest='min',
                        type=int,
                        default=0)
    parser.add_argument('--max',
                        action='store',
                        dest='max',
                        type=int,
                        default=1)
    parser.add_argument('--prefix',
                        action='store',
                        dest='prefix',
                        default='node')
    parser.add_argument('--plan',
                        action='store',
                        dest='plan',
                        default='2gb')
    parser.add_argument('--location',
                        action='store',
                        dest='location',
                        default='fra1')
    parser.add_argument('--image',
                        action='store',
                        dest='image',
                        default='debian-7-0-x64')
    parser.add_argument('--password',
                        action='store',
                        dest='password',
                        default='s4ltcl0udl1n123')
    parser.add_argument('--pubkeyfile',
                        action='store',
                        dest='pubkeyfile',
                        default='/Users/arnoldbechtoldt/.ssh/id_rsa.pub')
    parser.add_argument('--saltmaster',
                        action='store_true',
                        dest='saltmaster',
                        default=False)
    parser.add_argument('--saltmaster_address',
                        action='store',
                        dest='saltmaster_address',
                        default='127.0.0.1')
    parser.add_argument('--token',
                        action='store',
                        dest='token',
                        required=True)
    parser.add_argument('--ssh-keys',
                        action='store',
                        dest='ssh_keys',
                        required=True)
    parser.add_argument('--script-url',
                        action='store',
                        dest='script_url',
                        required=True)

    parser_results = parser.parse_args()
    min_number = parser_results.min
    max_number = parser_results.max
    prefix = parser_results.prefix
    plan = parser_results.plan
    location = parser_results.location
    image = parser_results.image
    password = parser_results.password
    #pubkeyfile = parser_results.pubkeyfile
    saltmaster = parser_results.saltmaster
    saltmaster_address = parser_results.saltmaster_address
    token = parser_results.token
    _ssh_keys = parser_results.ssh_keys
    script_url = parser_results.script_url

    ssh_keys = []
    for key_id in _ssh_keys.split(','):  # TODO use lambda?
        ssh_keys.append(int(key_id))

    current_number = min_number
    new_nodes = []
    while current_number <= max_number:
        label = '{}{}'.format(prefix, current_number)
        node = digitalocean.Droplet(token=token,
                                    name=label,
                                    region=location,
                                    image=image,
                                    size_slug=plan,
                                    ssh_keys=ssh_keys,
                                    ipv6=False,
                                    private_networking=True,
                                    backups=False)
        new_nodes.append(node)
        current_number = current_number + 1

    manager = digitalocean.Manager(token=token)
    all_nodes_ids = []
    for node in new_nodes:
        print("Creating node {}".format(node.name))
        node.create()
        sleep(0.5)
        all_nodes_ids.append(node.id)

    created_nodes_ids = []
    while True and len(all_nodes_ids) != len(created_nodes_ids):
        install_nodes = []
        for node_id in all_nodes_ids:
            if node_id in created_nodes_ids:
                continue
            try:
                _node = manager.get_droplet(node_id)
            except:
                continue

            if _node.status != 'active':
                continue
            install_nodes.append(_node.ip_address)
            node_names[_node.ip_address] = _node.name  # TODO use install_nodes (OrderedDict)
            created_nodes_ids.append(_node.id)

        if install_nodes:
            sleep(15)
            install_salt(script_url,
                         hostnames=install_nodes,
                         password=password,
                         master=saltmaster,
                         master_address=saltmaster_address,
                         image=image)
        else:
            sleep(5)


if __name__ == '__main__':
    exit(main())
