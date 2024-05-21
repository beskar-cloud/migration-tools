""" OpenStack project migrator library """

import re
import pprint
import time
import os
import os.path

import paramiko
import openstack
from keystoneauth1.identity import v3
from keystoneauth1 import session

def wait_for_keypress(msg="Press Enter to continue..."):
    """ wait for enter keypress """
    return input("Press Enter to continue...")

def get_resource_names_ids(resources):
    """ parses list of resource names/IDs separated by space of comma returned as list of strings or None """
    if isinstance(resources, str) and resources:
        return resources.replace(","," ").split()
    return None

def trim_dict(dict_data, allowed_keys=None, denied_keys=None):
    """ transform input dictionary and filter its keys with allowed_keys and denied_keys sequences """
    int_allowed_keys = allowed_keys if allowed_keys else tuple()
    int_denied_keys = denied_keys if denied_keys else tuple()
    if int_allowed_keys:
        return {i_key: dict_data[i_key] for i_key in dict_data if i_key in int_allowed_keys}
    if int_denied_keys:
        return {i_key: dict_data[i_key] for i_key in dict_data if i_key not in int_denied_keys}
    return dict_data

def executed_as_admin_user_in_ci():
    """ identity the script user within CI pipeline """
    return os.environ.get('GITLAB_USER_LOGIN') in ('246254', '252651', 'Jan.Krystof', 'moravcova', '469240', 'Josef.Nemec', '247801')

def executed_in_ci():
    """ detect CI environment """
    envvar_names = ('CI_JOB_NAME', 'CI_REPOSITORY_URL', 'GITLAB_USER_LOGIN')
    return {i_envvar_name in os.environ for i_envvar_name in envvar_names} == {True}


def get_ostack_project_names(project_name):
    """ get source and destination ostack project names """
    if '->' in project_name:
        return project_name.split('->', 1)
    return project_name, project_name

def get_destination_subnet(source_subnet):
    """ LUT for networks """
    subnet_mapping = {
        # TODO: shared

        # group project internal network
        "group-project-network-subnet": "group-project-network-subnet"
        }
    if source_subnet in subnet_mapping.keys():
        return subnet_mapping[source_subnet]
    return None

def get_destination_router(source_router):
    """ LUT for networks """
    router_mapping = {
        # TODO: shared

        # group project internal network
        "router": "group-project-router"
        }
    if source_router in router_mapping.keys():
        return router_mapping[source_router]
    return None


def normalize_table_data_field(data_field):
    """ normalize single data field (single data insert) """
    int_dict = {}
    i_name_key = '@name'
    for i_data_field_item in data_field:
        i_value_key = [ i_k for i_k in i_data_field_item.keys() if i_k != i_name_key][0]
        int_dict[i_data_field_item[i_name_key]] = i_data_field_item[i_value_key]
    return int_dict

def normalize_table_data(data):
    """ normalize whole table data """
    int_list = []
    for i_data_field in data:
        int_list.append(normalize_table_data_field(i_data_field['field']))
    return int_list

def get_dst_resource_name(args, name=""):
    """ translate original name to destination one """
    return f"{args.destination_entity_name_prefix}{name}"

def get_dst_resource_desc(args, desc="", fields=None):
    """ translate original description to destination one and fill in optional fields """
    if '{}' in args.destination_entity_description_suffix and fields:
        return f"{desc}{args.destination_entity_description_suffix.format(fields)}"
    return f"{desc}{args.destination_entity_description_suffix}"

def get_openrc(file_handle):
    """ parse and return OpenRC file """
    openrc_vars = {}

    for line in file_handle:
        match = re.match(r'^export (\w+)=(.+)$', line.strip())
        if match:
            openrc_vars[match.group(1)] = match.group(2).strip('"')
    return openrc_vars


def get_ostack_connection(openrc_vars):
    """ """
    auth_args = {
        'auth_url': openrc_vars.get('OS_AUTH_URL'),
        'username': openrc_vars.get('OS_USERNAME'),
        'password': openrc_vars.get('OS_PASSWORD'),
        'project_name': openrc_vars.get('OS_PROJECT_NAME'),
        'project_domain_name': openrc_vars.get('OS_PROJECT_DOMAIN_NAME'),
        'user_domain_name': openrc_vars.get('OS_USER_DOMAIN_NAME'),
        'project_domain_id': openrc_vars.get('OS_PROJECT_DOMAIN_ID'),
        'user_domain_id': openrc_vars.get('OS_USER_DOMAIN_ID'),
    }
    connection_args = {
        'compute_api_version': openrc_vars.get('OS_COMPUTE_API_VERSION'),
        'identity_api_version': openrc_vars.get('OS_IDENTITY_API_VERSION'),
        'volume_api_version': openrc_vars.get('OS_VOLUME_API_VERSION')
    }
    auth = v3.Password(**auth_args)
    ostack_sess = session.Session(auth=auth)
    ostack_conn = openstack.connection.Connection(session=ostack_sess, **connection_args)
    return ostack_conn

def get_ostack_project(ostack_connection, project_name):
    project = None
    for i_project in ostack_connection.list_projects():
        if i_project.name == project_name:
            project = i_project
    return project

def get_ostack_project_type(ostack_connection, project):
    """ detect project type, return 'group' / 'personal' / 'other' """
    if project.name in [ i_user.name for i_user in ostack_connection.list_users() ]:
        return "personal"
    return "group"

def get_ostack_project_security_groups(ostack_connection, project=None):
    security_groups = []
    if project:
        for i_security_group in ostack_connection.network.security_groups():
            if i_security_group.tenant_id == project.id:
                security_groups.append(i_security_group)
        return security_groups
    return tuple(ostack_connection.network.security_groups())

def get_ostack_project_keypairs(ostack_connection, project=None):
    return ostack_connection.list_keypairs()
def get_ostack_project_keypairs2(ostack_connection, project=None):
    return list(ostack_connection.compute.keypairs())


def get_ostack_project_servers(ostack_connection, project=None):
    return tuple(ostack_connection.compute.servers())

def get_ostack_project_volumes(ostack_connection, project=None):
    return ostack_connection.block_store.volumes()

def get_resource_details(resources):
    """ inspect resources """
    for i_resource in resources:
        print(i_resource)
        pprint.pprint(i_resource)

def remote_cmd_exec(hostname, username, key_filename, command):
    """ executes remote command, returs stdout, stderr and exit-code or Exception """
    # Create SSH client
    ssh_client = paramiko.SSHClient()
    # Automatically add untrusted hosts
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ecode = None

    try:
        # Connect to the remote host
        pkey = paramiko.RSAKey.from_private_key_file(key_filename)
        ssh_client.connect(hostname, username=username, pkey=pkey, look_for_keys=False)

        # Execute the command, read the output and close
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ecode = stdout.channel.recv_exit_status()
        ssh_client.close()

        return output, error, ecode

    except Exception as e:
        print("Error:", e)
        return None, None, e


def assert_entity_ownership(entities, project):
    """ assert that all supplied entities belong to given project """
    for i_entity in entities:
        assert i_entity.project_id == project.id, f"Entity belongs to expected project (id: {project.id})"




def log_or_assert(args, msg, condition, trace_details=None):
    """ log, assert, dump state """
    if not condition:
        with open(args.exception_trace_file, "w", encoding="utf-8") as file:
            file.write(f"{msg}\n{pprint.pformat(trace_details)}\n\n{locals()}\n")
    assert condition, msg
    args.logger.info(msg)


def wait_for_ostack_server_status(ostack_connection, server_name_or_id, server_status, timeout=600):
    """ wait for VM server getting expected state """
    int_start_timestamp = time.time()
    int_server = ostack_connection.compute.find_server(server_name_or_id)
    int_server_status = None
    while True:
        if time.time() > (int_start_timestamp + timeout):
            break
        int_server_status = ostack_connection.compute.find_server(int_server.id).status
        if int_server_status == server_status:
            break
        time.sleep(5)

    return int_server_status

def wait_for_ostack_volume_status(ostack_connection, volume_name_or_id, volume_status, timeout=300):
    """ wait for volume getting expected state """
    int_start_timestamp = time.time()
    int_volume = ostack_connection.block_storage.find_volume(volume_name_or_id)
    int_volume_status = None
    while True:
        if time.time() > (int_start_timestamp + timeout):
            break
        int_volume_status = ostack_connection.block_storage.find_volume(int_volume.id).status
        if int_volume_status == volume_status:
            break
        time.sleep(5)


    return int_volume_status

def server_detect_floating_address(server):
    """ return True if server has attached floating IP address otherwise False """
    for _, i_ip_details in server.addresses.items():
        for i_ip_detail in i_ip_details:
            if str(i_ip_detail.get('version')) == '4' and i_ip_detail.get('OS-EXT-IPS:type') == 'floating':
                return True
    return False

def get_server_floating_ip_port(ostack_connection, server):
    """ set server's port where to put FIP, otherwise None """
    for i_port in ostack_connection.network.ports(device_id=server.id):
        for i_port_ip in i_port.fixed_ips:
            for i_ip_prefix in ('192.', '10.', '172.'):
                if str(i_port_ip.get('ip_address')).startswith(i_ip_prefix):
                    return i_port
    return None
