""" OpenStack migrator - OpenStack library """

import copy
import inspect
import ipaddress
import math
import os.path

import openstack
import openstack.exceptions
import xmltodict

import clib
from lib import log_or_assert, get_dst_resource_name, get_dst_secgroup_name, get_dst_resource_desc, remote_cmd_exec, normalize_table_data, trim_dict, wait_for_ostack_volume_status


def get_destination_network(source_network):
    """ LUT for networks """
    network_mapping = {
        # shared
        "78-128-250-pers-proj-net": "internal-ipv4-general-private",
        "147-251-115-pers-proj-net": "internal-ipv4-general-private",
        "public-muni-v6-432": "external-ipv6-general-public",
        # external
        "public-muni-147-251-21-GROUP": "external-ipv4-general-public",
        "public-cesnet-78-128-250-PERSONAL": "external-ipv4-general-public",
        "public-cesnet-78-128-251-GROUP": "external-ipv4-general-public",
        "provider-public-cerit-sc-147-251-253": "external-ipv4-general-public",
        "public-muni-147-251-115-PERSONAL": "external-ipv4-general-public",
        "public-muni-147-251-124-GROUP": "external-ipv4-general-public",
        "public-cesnet-195-113-167-GROUP": "external-ipv4-general-public",
        "public-muni-147-251-11-128-254": "external-ipv4-general-public",
        "public-muni-CERIT-FI-147-251-88-132-254": "external-ipv4-general-public",
        "public-muni-CSIRT-MU-217-69-96-64-240": "external-ipv4-general-public",
        "public-muni-csirt-147-251-125-16-31": "external-ipv4-general-public",
        "provider-public-cerit-sc-147-251-254": "external-ipv4-general-public",
        # group project internal network
        "group-project-network": "group-project-network",
        "bjbjbgroup-project-network": "group-project-network"
    }
    if source_network in network_mapping:
        return network_mapping[source_network]
    return None


def get_destination_flavor(source_flavor):
    """ LUT for flavors """
    flavor_mapping = {
        # 'eph.16cores-60ram' # nemusime resit neni pouzit u zadneho projektu v g1
        # 'eph.8cores-30ram': 'c2.8core-30ram' # nemusime resit neni pouzit u zadneho projektu v g1
        # 'eph.8cores-60ram': 'c3.8core-60ram' # nemusime resit neni pouzit u zadneho projektu v g1
        'hdn.cerit.large-35ssd-ephem': 'p3.4core-8ram',  # nesedi velikost disku v G2 je 80 misto 35
        'hdn.cerit.large-ssd-ephem': 'p3.4core-8ram',  # ok
        'hdn.cerit.medium-35ssd-ephem': 'p3.2core-4ram',  # nesedi velikost disku v G2 je 80 misto 35
        'hdn.cerit.xxxlarge-ssd-ephem': 'p3.8core-60ram',  # ok
        # 'hdn.medium-ssd-ephem': # nemusime resit neni pouzit u zadneho projektu v g1
        'hpc.12core-64ram-ssd-ephem-500': 'c3.12core-64ram-ssd-ephem-500',  # neni v G2 a je potreba
        'hpc.16core-128ram': 'c3.16core-128ram',  # neni v G2 a je potreba
        'hpc.16core-256ram': 'c3.16core-256ram',  # neni v G2 a je potreba
        'hpc.16core-32ram': 'c2.16core-30ram',  # ok
        'hpc.16core-32ram-100disk': 'c3.16core-32ram-100disk',  # neni v G2 a je potreba
        'hpc.16core-64ram-ssd-ephem': 'hpc.16core-64ram-ssd',  # neni v G2 a je potreba
        'hpc.16core-64ram-ssd-ephem-500': 'p3.16core-60ram',  # ok
        'hpc.18core-48ram': 'c2.18core-45ram',  # ok
        'hpc.18core-64ram-dukan': 'c2.24core-60ram',  # nemusime resit
        'hpc.24core-96ram-ssd-ephem': 'hpc.24core-96ram-ssd',  # nemusime resit
        'hpc.30core-128ram-ssd-ephem-500': 'c3.30core-128ram-ssd-ephem-500',  # neni v G2 a je potreba
        'hpc.30core-256ram': 'c3.30core-240ram',  # ok
        'hpc.30core-64ram': 'c3.30core-60ram',  # ok
        'hpc.4core-16ram-ssd-ephem': 'p3.4core-16ram',  # ok
        'hpc.4core-16ram-ssd-ephem-500': 'p3.4core-16ram',  # ok
        'hpc.4core-4ram': 'e1.medium',  # nemusime resit
        'hpc.8core-128ram': 'c3.8core-120ram',  # OK
        'hpc.8core-16ram': 'c2.8core-16ram',  # ok
        'hpc.8core-16ram-ssd-ephem': 'p3.8core-16ram',  # nemusime resit
        'hpc.8core-256ram': None,  # nemusime resit
        'hpc.8core-32ram-dukan': 'c2.8core-30ram',  # nemusime resit
        'hpc.8core-32ram-ssd-ephem': 'p3.8core-30ram',  # ok
        'hpc.8core-32ram-ssd-rcx-ephem': 'p3.8core-30ram',  # ok
        'hpc.8core-64ram-ssd-ephem-500': 'p3.8core-60ram',  # ok
        'hpc.8core-8ram': 'e1.1xlarge',  # v G2 je o 20 GB mensi disk
        'hpc.hdh-ephem': 'hpc.hdh',  # neni a je potreba
        'hpc.hdn.30core-128ram-ssd-ephem-500': 'c3.hdn.30core-128ram-ssd-ephem-500',  # neni potreba
        'hpc.hdn.4core-16ram-ssd-ephem-500': 'p3.4core-16ram',  # neni potreba
        # 'hpc.ics-gladosag-full': 'c3.ics-gladosag-full', # neni potreba
        'hpc.large': 'g2.3xlarge',  # ok
        'hpc.medium': 'c2.8core-30ram',  # ok
        'hpc.small': 'c2.4core-16ram',  # ok
        'hpc.xlarge': None,  # neni v G2
        'hpc.xlarge-memory': 'c3.xlarge-memory',  # neni v G2
        'elixir.60core-128ram': 'c3.60core-120ram',
        'standard.16core-32ram': 'g2.2xlarge',  # ok
        'standard.20core-128ram': 'e1.20core-128ram',  # neni potreba
        'standard.20core-256ram': 'e1.20core-256ram',  # neni v G2
        'standard.2core-16ram': 'c3.2core-16ram',  # ok
        'standard.large': 'e1.large',  # ok pripadne jeste c3.4core-8ram
        'standard.medium': 'e1.medium',  # o 2 vice CPU
        'standard.memory': 'c3.2core-30ram',  # pripadne i c2.2core-30ram
        'standard.one-to-many': 'c3.24core-60ram',  # v G2 je o 4 vice CPU
        'standard.small': 'e1.small',  # 2x vice ram a CPU u G2
        'standard.tiny': 'e1.tiny',  # 2x vice ram a CPU u G2
        'standard.xlarge': 'e1.2xlarge',  # o 4 vice CPU G2
        'standard.xlarge-cpu': 'e1.2xlarge',  # ok
        'standard.xxlarge': 'c2.8core-30ram',  # ok
        'standard.xxxlarge': 'c3.8core-60ram',  # ok
        'csirtmu.tiny1x2': 'g2.1core-2ram', # ok
        'csirtmu.tiny1x4': 'g2.1core-4ram', # ok
        'csirtmu.small2x4': 'g2.2core-4ram', # ok
        'csirtmu.small2x8': 'g2.tiny', # ok
        'csirtmu.medium4x8': 'g2.small', # ok
        'csirtmu.medium4x16': 'g2.medium', # ok
        'csirtmu.large8x16': 'g2.large', # ok
        'csirtmu.large4x32': 'g2.4core-30ram', # ok
        'csirtmu.large8x32': 'g2.8core-30ram', # ok
        'csirtmu.jumbo16x32': 'g2.2xlarge', # ok
        'csirtmu.jumbo8x64': 'g2.8core-60ram', # ok
        'csirtmu.jumbo16x64': 'g2.3xlarge' # ok
    }
    assert source_flavor in flavor_mapping, "Source flavor can be mapped to destination one"
    assert flavor_mapping[source_flavor], "Source flavor mapping is not valid"
    return flavor_mapping[source_flavor]


def create_destination_networking(args, src_ostack_conn, dst_ostack_conn, src_project, dst_project, src_network_name):
    """ Create matching OpenStack networking (network, subnet, router) """
    # read source network details
    src_network = src_ostack_conn.network.find_network(src_network_name, project_id=src_project.id)
    # read matching subnets details
    src_subnets = [src_ostack_conn.network.find_subnet(i_src_subnet_id) for i_src_subnet_id in src_network.subnet_ids]
    # read linked routers
    src_network_router_ports = [i_src_router_port for i_src_router_port in src_ostack_conn.list_ports(filters={'network_id': src_network.id}) if
                                i_src_router_port.device_owner == 'network:router_interface']
    src_network_routers_subnets = [(src_ostack_conn.network.find_router(router_port.device_id), [rp_fixed_ip['subnet_id'] for rp_fixed_ip in router_port.fixed_ips if 'subnet_id' in rp_fixed_ip]) for
                                   router_port in src_network_router_ports]

    # read external network
    dst_ext_network = dst_ostack_conn.network.find_network(args.destination_ipv4_external_network)

    # create network
    dst_network_name = get_dst_resource_name(args, src_network_name)
    dst_network = dst_ostack_conn.network.find_network(dst_network_name,
                                                       project_id=dst_project.id)
    if not dst_network:
        dst_network = dst_ostack_conn.network.create_network(name=dst_network_name,
                                                             project_id=dst_project.id,
                                                             mtu=src_network.mtu,
                                                             description=get_dst_resource_desc(args,
                                                                                               src_network.description,
                                                                                               src_network.id),
                                                             port_security_enabled=src_network.is_port_security_enabled)

    # create subnets
    dst_subnets = []
    subnet_mapping = {}
    for i_src_subnet in src_subnets:
        i_dst_subnet_name = get_dst_resource_name(args, i_src_subnet.name)
        i_dst_subnet = dst_ostack_conn.network.find_subnet(i_dst_subnet_name, project_id=dst_project.id)
        if not i_dst_subnet:
            i_dst_subnet = dst_ostack_conn.network.create_subnet(network_id=dst_network.id,
                                                                 name=i_dst_subnet_name,
                                                                 cidr=i_src_subnet.cidr,
                                                                 ip_version=i_src_subnet.ip_version,
                                                                 enable_dhcp=i_src_subnet.is_dhcp_enabled,
                                                                 project_id=dst_project.id,
                                                                 allocation_pools=i_src_subnet.allocation_pools,
                                                                 gateway_ip=i_src_subnet.gateway_ip,
                                                                 host_routes=i_src_subnet.host_routes,
                                                                 dns_nameservers=i_src_subnet.dns_nameservers,
                                                                 description=get_dst_resource_desc(args,
                                                                                                   i_src_subnet.description,
                                                                                                   i_src_subnet.id))
        subnet_mapping[i_src_subnet.id] = i_dst_subnet.id
        dst_subnets.append(i_dst_subnet)

    # create router(s) and associate with subnet(s) (if needed)
    dst_network_routers = []
    for i_src_network_router, i_src_network_router_subnets in src_network_routers_subnets:

        i_dst_network_router_name = get_dst_resource_name(args, i_src_network_router.name)
        i_dst_network_router = dst_ostack_conn.network.find_router(i_dst_network_router_name,
                                                                   project_id=dst_project.id)
        if not i_dst_network_router:
            i_dst_network_router = dst_ostack_conn.network.create_router(name=i_dst_network_router_name,
                                                                         description=get_dst_resource_desc(args,
                                                                                                           i_src_network_router.description,
                                                                                                           i_src_network_router.id),
                                                                         project_id=dst_project.id,
                                                                         external_gateway_info={"network_id": dst_ext_network.id})
            for i_src_network_router_subnet in i_src_network_router_subnets:
                # TODO: Principally there may be also foreign subnets, find more general solution
                if i_src_network_router_subnet in subnet_mapping:
                    dst_ostack_conn.add_router_interface(i_dst_network_router, subnet_id=subnet_mapping[i_src_network_router_subnet])

        dst_network_routers.append(i_dst_network_router)

    dst_network = dst_ostack_conn.network.find_network(dst_network.id,
                                                       project_id=dst_project.id)

    return dst_network, dst_subnets, dst_network_routers


def get_or_create_dst_server_networking_v1(args,
                                           source_project_conn, destination_project_conn,
                                           source_project, destination_project,
                                           source_server):
    """ assure created server networking (get or create) """
    server_network_addresses = []
    for i_source_network_name, i_source_network_addresses in source_server.addresses.items():
        i_destination_network_name = get_destination_network(i_source_network_name)

        if not i_destination_network_name:
            # if network is not mapped we need to create matching one
            i_dst_network, _, _ = create_destination_networking(args,
                                                                source_project_conn, destination_project_conn,
                                                                source_project, destination_project,
                                                                i_source_network_name)
        i_destination_network = destination_project_conn.network.find_network(i_destination_network_name or i_dst_network.id, #pylint: disable=possibly-used-before-assignment
                                                                              project_id=destination_project.id)
        log_or_assert(args, f"F.3 Destination network exists ({i_destination_network})", i_destination_network)

        server_network_addresses.append({'dst-network': i_destination_network,
                                         'src-network-addresses': {'network-name': i_source_network_name,
                                                                   'addresses': i_source_network_addresses}})
    return server_network_addresses


def get_or_create_dst_server_networking_v2(args,
                                           source_project_conn, destination_project_conn,
                                           source_project, destination_project,
                                           source_server):
    """ assure created server networking (get or create) """
    server_network_addresses = []
    for i_src_server_port in source_project_conn.network.ports(device_id=source_server.id):
        i_src_server_port_network_name = source_project_conn.network.find_network(i_src_server_port.network_id).name
        i_dst_server_port_network_name = get_destination_network(i_src_server_port_network_name)

        args.logger.debug(f"Assuring VM ({source_server.name}) network {i_src_server_port_network_name} -> {i_dst_server_port_network_name}")
        if not i_dst_server_port_network_name:
            # if network is not mapped we need to create matching one
            i_dst_network, _, _ = create_destination_networking(args,
                                                                source_project_conn, destination_project_conn,
                                                                source_project, destination_project,
                                                                i_src_server_port_network_name)
        i_destination_network = destination_project_conn.network.find_network(i_dst_server_port_network_name or i_dst_network.id, #pylint: disable=possibly-used-before-assignment
                                                                              project_id=destination_project.id)
        # network may be shared (created in different project), so let's ask again w/o project_id selector
        if not i_destination_network:
            i_destination_network = destination_project_conn.network.find_network(i_dst_server_port_network_name or i_dst_network.id)
        log_or_assert(args, f"F.3 Destination network exists ({i_destination_network})", i_destination_network)

        server_network_addresses.append({'dst-network': i_destination_network,
                                         'src-network-addresses': {'network-name': i_src_server_port_network_name,
                                                                   'addresses': source_server.addresses.get(i_src_server_port_network_name, None),
                                                                   'port': i_src_server_port}})
    args.logger.debug(f"VM ({source_server.name}) network addresses dump: {server_network_addresses}")

    return server_network_addresses


def get_or_create_dst_server_networking(args,
                                        source_project_conn, destination_project_conn,
                                        source_project, destination_project,
                                        source_server):
    """ assure created server networking (get or create) """
    server_network_addresses = []
    for i_src_server_port_network_name, i_src_server_port_network_addresses in source_server.addresses.items():
        i_src_server_ip_addr = [(i_item['addr']) for i_item in i_src_server_port_network_addresses
                                if i_item['OS-EXT-IPS:type'] == 'fixed'][0]
        i_src_server_mac_addr = [(i_item['OS-EXT-IPS-MAC:mac_addr']) for i_item in i_src_server_port_network_addresses
                                 if i_item['OS-EXT-IPS:type'] == 'fixed'][0]
        i_src_server_ports = find_ostack_port(source_project_conn, i_src_server_mac_addr, i_src_server_ip_addr, device=source_server)
        log_or_assert(args, f"F.3 Source server ostack fixed IP address detected ({i_src_server_ip_addr})", i_src_server_ip_addr)
        log_or_assert(args, f"F.3 Source server ostack fixed MAC address detected ({i_src_server_mac_addr})", i_src_server_mac_addr)
        log_or_assert(args, "F.3 Source server ostack port(s) detected", i_src_server_ports)
        log_or_assert(args, "F.3 Source server ostack single (unambiguous) port detected", len(i_src_server_ports) == 1)
        i_src_server_port = i_src_server_ports[0]
        args.logger.debug(f"Source VM ({source_server.name}) network port detected (ip:{i_src_server_ip_addr}, mac:{i_src_server_mac_addr}, port:{i_src_server_port})")
        i_dst_server_port_network_name = get_destination_network(i_src_server_port_network_name)
        args.logger.debug(f"Assuring VM ({source_server.name}) src -> dst network mapping {i_src_server_port_network_name} -> {i_dst_server_port_network_name}")

        i_destination_network = None
        if i_dst_server_port_network_name:
            # we got network name mapping, it is likely that destination network exists
            # detect whether we have destination network searching in the destination project
            i_destination_network = destination_project_conn.network.find_network(i_dst_server_port_network_name,
                                                                                  project_id=destination_project.id)
        args.logger.debug(f"Destination network searched in the destination project ({i_destination_network})")

        if i_dst_server_port_network_name and not i_destination_network:
            # we got network name mapping, it is likely that destination network exists, but not in the project
            # detect whether we have destination network searching globally
            try:
                i_destination_network = destination_project_conn.network.find_network(i_dst_server_port_network_name)
            except openstack.exceptions.DuplicateResource:
                pass
        args.logger.debug(f"Destination network searched in the project and then globally ({i_destination_network})")

        if (not i_dst_server_port_network_name) or (i_dst_server_port_network_name and not i_destination_network):
            # if network is not mapped or mapped and not found we need to create matching one
            i_dst_network, _, _ = create_destination_networking(args,
                                                                source_project_conn, destination_project_conn,
                                                                source_project, destination_project,
                                                                i_src_server_port_network_name)
            i_destination_network = i_dst_network

        log_or_assert(args, f"F.3 Destination network exists ({i_destination_network})", i_destination_network)
        server_network_addresses.append({'dst-network': i_destination_network,
                                         'src-network-addresses': {'network-name': i_src_server_port_network_name,
                                                                   'addresses': source_server.addresses.get(i_src_server_port_network_name, None),
                                                                   'port': i_src_server_port}})
    args.logger.debug(f"VM ({source_server.name}) network addresses dump: {server_network_addresses}")

    return server_network_addresses


def get_dst_server_flavor(args, src_server, dst_ostack_conn):
    """ translate and return destination server flavor object """
    source_server_flavor_name = src_server.flavor.name
    destination_server_flavor_name = get_destination_flavor(source_server_flavor_name)

    log_or_assert(args,
                  f"F.5 Source to Destination flavor mapping succeeeded ({source_server_flavor_name}->{destination_server_flavor_name})",
                  destination_server_flavor_name)
    destination_server_flavor = dst_ostack_conn.compute.find_flavor(destination_server_flavor_name)
    log_or_assert(args,
                  "F.6 Destination OpenStack flavor exists",
                  destination_server_flavor)

    return destination_server_flavor


def get_dst_server_flavor_name_noassert(args, src_server, dst_ostack_conn):
    """ translate and return destination server flavor name and object as tuple """
    source_server_flavor_name = src_server.flavor.name
    destination_server_flavor_name = get_destination_flavor(source_server_flavor_name)

    if destination_server_flavor_name:
        args.logger.info(f"F.5 Source to Destination flavor mapping succeeeded ({source_server_flavor_name}->{destination_server_flavor_name})")

        destination_server_flavor = dst_ostack_conn.compute.find_flavor(destination_server_flavor_name)

        if destination_server_flavor:
            args.logger.info(f"F.6 Destination OpenStack flavor exists in destination project ({destination_server_flavor_name})")
        else:
            args.logger.error(f"F.6 Destination OpenStack flavor does not exist in destination project ({destination_server_flavor_name}). Add flavor access in cloud-entities!")
    else:
        args.logger.error(f"F.5 Source to Destination flavor mapping failed ({source_server_flavor_name}->{destination_server_flavor_name}). You need to update flavor mapping LUT table!")

    return destination_server_flavor_name


def download_source_keypairs(args):
    """ download/receive source openstack keypairs from ceph migrator host as xml formatted sql dump """
    reply_stdout, _, reply_ecode = remote_cmd_exec(args.ceph_migrator_host,
                                                   args.ceph_migrator_user,
                                                   args.ceph_migrator_sshkeyfile.name,
                                                   f"cat {args.source_keypair_xml_dump_file}")
    assert reply_ecode == 0, "Keypairs received"
    table_dictdata = xmltodict.parse(reply_stdout)
    table_data_dictdata = table_dictdata['mysqldump']['database']['table_data']['row']
    return normalize_table_data(table_data_dictdata)


def filter_keypairs(keypairs, filter_filed_name, filter_field_value):
    """ filter keypairs list of dicts by value of a field """
    return [i_keypair for i_keypair in keypairs if i_keypair.get(filter_filed_name, "") == filter_field_value]


def create_keypair(args, ostack_connection, keypair):
    """ create openstack keypair object """
    return ostack_connection.compute.create_keypair(name=get_dst_resource_name(args, keypair['name']),
                                                    public_key=keypair['public_key'], type=keypair['type'])


def get_src_server_keypair(args, source_keypairs, src_server):
    """ obtain single keypair from list of all source server keypairs """
    # select keypairs based on key_name only
    source_keypairs_by_name = filter_keypairs(source_keypairs, "name", src_server.key_name)
    log_or_assert(args,
                  f"F.7 Source OpenStack server keypair found ({src_server.key_name}).",
                  source_keypairs_by_name,
                  msg_guidance="Current source OpenStack cloud keypair dump is outdated already and does not contain mentioned keypair. "
                               "Re-dump source OpenStack keypairs to ceph migrator server node and retry migration.")
    # select keypairs based on key_name and user_id
    source_keypairs_by_name_and_user = filter_keypairs(source_keypairs_by_name, "user_id", src_server.user_id)
    log_or_assert(args,
                  f"F.7 Single (unambiguous) Source OpenStack server keypair found ({src_server.key_name}) when searching with key_name only.",
                  len(source_keypairs_by_name_and_user) > 0 or len(source_keypairs_by_name) < 2,
                  msg_guidance="We encountered situation when we are unable to detect source keypair. Search with (key_name, used_id) returned "
                               "no result and search with key_name only returned multiple results. "
                               "Most likely it is necessary to reimplement olib.get_or_create_dst_server_keypair().")
    if not source_keypairs_by_name_and_user:
        args.logger.warning(f"F.7 No source keypair found when selecting by (key_name={src_server.key_name}, used_id={src_server.user_id}). "
                            "Using selection by key_name only.")
        return source_keypairs_by_name[0]
    if len(source_keypairs_by_name_and_user) > 1:
        args.logger.warning(f"F.7 Multiple source keypairs found when searching with (key_name={src_server.key_name}, used_id={src_server.user_id}). "
                            "Picking the first detected keypair.")
    return source_keypairs_by_name_and_user[0]


def get_or_create_dst_server_keypair(args, source_keypairs, src_server, dst_ostack_conn):
    """ assure destination cloud keypair exists """
    if destination_server_keypairs := [i_keypair for i_keypair in dst_ostack_conn.list_keypairs()
                                       if i_keypair.name == get_dst_resource_name(args,
                                                                                  src_server.key_name)]:
        destination_server_keypair = destination_server_keypairs[0]
        log_or_assert(args,
                      f"F.8 Destination OpenStack server keypair found already ({destination_server_keypair.name})",
                      destination_server_keypair)
    else:
        if str(src_server.key_name) != 'None':
            destination_server_keypair = create_keypair(args,
                                                        dst_ostack_conn,
                                                        get_src_server_keypair(args, source_keypairs, src_server))
            args.logger.info("F.8 Destination OpenStack server keypair created")
        else:
            args.logger.info("F.8 Destination OpenStack server keypair not created as source server does not have it")
    if str(src_server.key_name) != 'None':
        log_or_assert(args,
                     f"F.9 Destination OpenStack server keypair exists ({destination_server_keypair.name})",
                     destination_server_keypair)
    else:
        args.logger.info("F.9 Destination OpenStack server does not have keypair")
        return None
    return destination_server_keypair


def create_security_groups(args, src_ostack_conn, dst_ostack_conn, src_security_group, dst_project, recursion_stack=None):
    """ create openstack security group[s] """
    int_recursion_stack = {} if recursion_stack is None else recursion_stack
    int_sg = dst_ostack_conn.network.create_security_group(name=get_dst_secgroup_name(args, src_security_group.name),
                                                           description=get_dst_resource_desc(args,
                                                                                             src_security_group.description,
                                                                                             src_security_group.id),
                                                           project_id=dst_project.id)
    int_recursion_stack[src_security_group.id] = int_sg.id

    for i_rule in src_security_group.security_group_rules:
        # browse security group rules
        i_mod_rule = trim_dict(i_rule, denied_keys=['id', 'project_id', 'tenant_id', 'revision_number', 'updated_at', 'created_at', 'tags', 'standard_attr_id', 'normalized_cidr'])
        i_mod_rule['security_group_id'] = int_sg.id
        i_mod_rule['project_id'] = dst_project.id
        i_mod_rule = {i_k: i_mod_rule[i_k] for i_k in i_mod_rule if i_mod_rule[i_k] is not None}
        if i_mod_rule.get('remote_group_id') is not None:
            if i_mod_rule['remote_group_id'] in int_recursion_stack:
                # keep reference to itself or known (already created) SGs
                i_mod_rule['remote_group_id'] = int_recursion_stack[i_mod_rule['remote_group_id']]
            # get linked source SG
            elif _src_sg := src_ostack_conn.network.find_security_group(i_mod_rule['remote_group_id']):
                if _dst_sg := dst_ostack_conn.network.find_security_group(get_dst_secgroup_name(args, _src_sg.name),
                                                                          project_id=dst_project.id):
                    i_mod_rule['remote_group_id'] = _dst_sg.id
                else:
                    int_linked_sg = create_security_groups(args, src_ostack_conn, dst_ostack_conn,
                                                           _src_sg, dst_project,
                                                           copy.deepcopy(int_recursion_stack))
                    i_mod_rule['remote_group_id'] = int_linked_sg.id
        try:
            dst_ostack_conn.network.create_security_group_rule(**i_mod_rule)
        except openstack.exceptions.ConflictException:
            pass

    return int_sg


def duplicate_ostack_project_security_groups(args, src_ostack_conn, dst_ostack_conn, src_project, dst_project):
    """ duplicate all projects's openstack security group[s] """

    src_project_security_groups = tuple(src_ostack_conn.network.security_groups(project_id=src_project.id))

    for i_src_security_group in src_project_security_groups:
        j_dst_security_group_found = False
        for j_dst_security_group in tuple(dst_ostack_conn.network.security_groups(project_id=dst_project.id)):
            if get_dst_secgroup_name(args, i_src_security_group.name) == j_dst_security_group.name and \
                    i_src_security_group.id in j_dst_security_group.description:
                j_dst_security_group_found = True
        if not j_dst_security_group_found:
            create_security_groups(args, src_ostack_conn, dst_ostack_conn, i_src_security_group, dst_project)

    return src_project_security_groups, tuple(dst_ostack_conn.network.security_groups(project_id=dst_project.id))


def get_or_create_dst_server_security_groups(args, src_ostack_conn, dst_ostack_conn, src_project, dst_project, src_server):
    """ assure equivalent security groups are created in destination cloud """
    dst_server_security_groups = []
    if src_server.security_groups:
        for i_src_server_security_group_name in {i_sg['name'] for i_sg in src_server.security_groups}:
            i_src_server_security_group = src_ostack_conn.network.find_security_group(i_src_server_security_group_name,
                                                                                      project_id=src_project.id)
            if i_dst_server_security_group := dst_ostack_conn.network.find_security_group(get_dst_secgroup_name(args,
                                                                                                                i_src_server_security_group.name),
                                                                                          project_id=dst_project.id):
                log_or_assert(args,
                              f"F.10 Destination OpenStack server security group found already ({i_dst_server_security_group.name})",
                              i_dst_server_security_group)
            else:
                args.logger.info("F.10 Destination OpenStack server matching security group not found and gets created.")
                i_dst_server_security_group = create_security_groups(args, src_ostack_conn, dst_ostack_conn,
                                                                     i_src_server_security_group, dst_project)
                log_or_assert(args,
                              f"F.10 Destination OpenStack server security group created ({i_dst_server_security_group.name})",
                              i_dst_server_security_group)

            log_or_assert(args,
                          f"F.11 Destination OpenStack server security group exists ({i_dst_server_security_group.name})",
                          i_dst_server_security_group)
            dst_server_security_groups.append(i_dst_server_security_group)
        log_or_assert(args,
                      "F.12 Destination OpenStack server - destination security groups exists",
                      dst_server_security_groups)
    else:
        args.logger.info("F.10 Source OpenStack server does not have any security groups linked.")

    return dst_server_security_groups


def get_server_block_device_mapping(args, server_volume_attachment, server_volume, server_root_device_name):
    """ return server block device mapping item """
    return {'source': {'block_storage_type': 'openstack-volume-ceph-rbd-image',
                       'volume_attachment_id': server_volume_attachment.id,
                       'volume_id': server_volume.id,
                       'ceph_pool_name': args.source_ceph_cinder_pool_name,
                       'ceph_rbd_image_name': server_volume.id},
            'destination': {'volume_size': server_volume.size,
                            'volume_name': get_dst_resource_name(args, server_volume.name),
                            'volume_description': server_volume.description,
                            'volume_id': None,
                            'ceph_pool_name': args.destination_ceph_cinder_pool_name,
                            'device_name': os.path.basename(server_volume_attachment.device),
                            'volume_bootable': server_root_device_name == server_volume_attachment.device}}


def create_server_block_device_mappings(args, src_ostack_conn, src_server, source_rbd_images):
    """ create description how are block devices connected to (src/dst) VM server """
    server_block_device_mappings = []
    # schema: [ {}, ... ]
    # where {} is following dict
    # { 'source': {'block_storage_type': 'openstack-volume-ceph-rbd-image', 'volume_attachment_id': <>, 'volume_id': <>,
    #              'ceph_pool_name': <pool-name>, 'ceph_rbd_image_name': <rbd-image-name>, 'ceph_rbd_image_size': <size-gb>}
    #             OR
    #             {'block_storage_type': 'ceph-rbd-image', 'ceph_pool_name': <pool-name>, 'ceph_rbd_image_name': <rbd-image-name>, 'ceph_rbd_image_size': <size-gb> } ]
    #   'destination': {'volume_size': <size-gb>, 'volume_id': <vol-id>, 'device_name': <dev-name>, 'volume_bootable': True/False}
    # }

    src_server_root_device_name = src_server.root_device_name
    log_or_assert(args,
                  f"F.20 Source OpenStack server - root device name received ({src_server_root_device_name})",
                  src_server_root_device_name)

    src_server_volume_attachments = tuple(src_ostack_conn.compute.volume_attachments(src_server.id))
    args.logger.debug(f"F.21 Source OpenStack server - volume attachments received {src_server_volume_attachments}")

    if src_server_root_device_name in [i_source_server_attachment.device for i_source_server_attachment in src_server_volume_attachments]:
        args.logger.info("F.22 Source OpenStack server - one of attached volume is attached as the root partition")

        # populate server_block_device_mappings
        for i_source_server_volume_attachment in src_server_volume_attachments:
            i_server_volume = src_ostack_conn.block_storage.find_volume(i_source_server_volume_attachment.volume_id)
            server_block_device_mappings.append(get_server_block_device_mapping(args, i_source_server_volume_attachment,
                                                                                i_server_volume, src_server_root_device_name))
    else:
        args.logger.info("F.22 Source OpenStack server - none of attached volumes is attached as the root partition. Seeking for root partition RBD image")

        src_ceph_ephemeral_rbd_image = f"{src_server.id}_disk"
        if src_ceph_ephemeral_rbd_image in source_rbd_images[args.source_ceph_ephemeral_pool_name]:

            args.logger.info(f"F.23 Source OpenStack server - Root partition found as RBD image {args.source_ceph_ephemeral_pool_name}/{src_ceph_ephemeral_rbd_image}")

            # get rbd image info / size
            src_ceph_ephemeral_rbd_image_data, _, _ = clib.ceph_rbd_image_info(args, args.source_ceph_ephemeral_pool_name,
                                                                               src_ceph_ephemeral_rbd_image)
            log_or_assert(args,
                          f"F.24 Source OpenStack ceph RBD image proper information received {src_ceph_ephemeral_rbd_image_data}",
                          src_ceph_ephemeral_rbd_image_data and 'size' in src_ceph_ephemeral_rbd_image_data)
            src_ceph_ephemeral_rbd_image_size = math.ceil(src_ceph_ephemeral_rbd_image_data['size'] / 1024 / 1024 / 1024)
            log_or_assert(args,
                          f"F.25 Source OpenStack ceph RBD image size calculated ({src_ceph_ephemeral_rbd_image_size})",
                          src_ceph_ephemeral_rbd_image_size)

            # populate server_block_device_mappings
            # initial disk
            server_block_device_mappings.append({'source': {'block_storage_type': 'ceph-rbd-image',
                                                            'volume_id': src_ceph_ephemeral_rbd_image,
                                                            'ceph_pool_name': args.source_ceph_ephemeral_pool_name,
                                                            'ceph_rbd_image_name': src_ceph_ephemeral_rbd_image,
                                                            'ceph_rbd_image_size': src_ceph_ephemeral_rbd_image_size},
                                                 'destination': {'volume_size': src_ceph_ephemeral_rbd_image_size,
                                                                 'volume_name': get_dst_resource_name(args,
                                                                                                      src_ceph_ephemeral_rbd_image),
                                                                 'volume_description': f"RBD {args.source_ceph_ephemeral_pool_name}/{src_ceph_ephemeral_rbd_image}",
                                                                 'volume_id': None,
                                                                 'ceph_pool_name': args.destination_ceph_cinder_pool_name,
                                                                 'device_name': os.path.basename(src_server_root_device_name),
                                                                 'volume_bootable': True}})

            # other disks attached to VM
            for i_source_server_volume_attachment in src_server_volume_attachments:
                i_server_volume = src_ostack_conn.block_storage.find_volume(i_source_server_volume_attachment.volume_id)
                server_block_device_mappings.append(get_server_block_device_mapping(args,
                                                                                    i_source_server_volume_attachment,
                                                                                    i_server_volume,
                                                                                    src_server_root_device_name))

    log_or_assert(args,
                  "F.26 Source OpenStack server - root partition detected",
                  server_block_device_mappings and server_block_device_mappings[0] and server_block_device_mappings[0]['source'])
    log_or_assert(args,
                  "F.27 Destination OpenStack server - root partition details generated",
                  server_block_device_mappings and server_block_device_mappings[0] and server_block_device_mappings[0]['destination'])

    return server_block_device_mappings


def create_dst_server_volumes_update_block_device_mappings(args, server_block_device_mappings, dst_ostack_conn, destination_image):
    """ create destination cloud volumes and final destination server to block storage mappings """
    out_server_block_device_mappings = copy.deepcopy(server_block_device_mappings)
    for i_dst_server_block_device_mapping in out_server_block_device_mappings:
        i_new_volume_args = {'name': i_dst_server_block_device_mapping['destination']['volume_name'],
                             'size': i_dst_server_block_device_mapping['destination']['volume_size'],
                             'description': get_dst_resource_desc(args,
                                                                  i_dst_server_block_device_mapping['destination']['volume_description'],
                                                                  i_dst_server_block_device_mapping['source']['volume_id'])}

        # TODO: this seems to be the only way how to create bootable volume using openstacksdk, check again
        if i_dst_server_block_device_mapping['destination']['volume_bootable']:
            i_new_volume_args['imageRef'] = destination_image.id

        i_new_volume = dst_ostack_conn.block_storage.create_volume(**i_new_volume_args)
        log_or_assert(args,
                      f"F.29 Destination OpenStack volume created (name:{i_new_volume.name}, id:{i_new_volume.id})",
                      i_new_volume)
        wait_for_ostack_volume_status(dst_ostack_conn, i_new_volume.id, 'available')
        log_or_assert(args,
                      f"F.30 Destination OpenStack volume available (name:{i_new_volume.name}, id:{i_new_volume.id})",
                      wait_for_ostack_volume_status(dst_ostack_conn, i_new_volume.id, 'available') == 'available')

        # remember volume ID
        i_dst_server_block_device_mapping['destination']['volume_id'] = i_new_volume.id

    for i_dst_server_block_device_mapping in out_server_block_device_mappings:
        log_or_assert(args,
                      f"F.31 Destination OpenStack volume IDs properly stored (id:{i_dst_server_block_device_mapping['destination']['volume_id']})",
                      i_dst_server_block_device_mapping['destination']['volume_id'])
    return out_server_block_device_mappings


def describe_server_network_connection(args, dst_ostack_conn, dst_project, netaddr_dict):
    """ create ostack server to network connection via network id or fixed-ip
        retults in single dictionary fed to conn.compute.create_server(...networks=[ <>, ...])
    """
    # netaddr_dict{ 'dst-network': Network,
    #               'src-network-addresses': {'network-name': <source-network-name>,
    #                                         'addresses': [ ... ],
    #                                         'port': <openstack.network.v2.port.Port object>} }
    func_name = inspect.currentframe().f_code.co_name
    msg_suffix = "Carefully check whether migrated VM is accessible and can communicate with outside world."
    src_port = netaddr_dict['src-network-addresses']['port']
    src_port_ip = src_port.fixed_ips[0]['ip_address']
    dst_network = netaddr_dict['dst-network']
    dst_port = None
    # detect already existing port
    dst_port_list = find_ostack_port(dst_ostack_conn, src_port.mac_address, src_port_ip, description_substr=src_port.id,
                                     project=dst_project, network=dst_network)
    if dst_port_list and len(dst_port_list) == 1:
        dst_port = dst_port_list[0]
        args.logger.debug(f"{func_name}() Reusing already existing ostack port. "
                          f"(mac: {src_port.mac_address}, ip: {src_port_ip}, desc: ~ {src_port.id}")
    else:
        try:
            args.logger.debug(f"{func_name}() Creating an ostack port. (mac: {src_port.mac_address}, ip: {src_port_ip}")
            dst_port_fixed_ip = {"subnet_id": dst_network.subnet_ids[0]}
            if isinstance(ipaddress.ip_address(src_port_ip), ipaddress.IPv4Address):
                # do not assign ipv6 public address (different CIDR and SLAAC in place)
                dst_port_fixed_ip['ip_address'] = src_port_ip
            dst_port = dst_ostack_conn.network.create_port(name=get_dst_resource_name(args, src_port.name or ''),
                                                           description=get_dst_resource_desc(args,
                                                                                             src_port.description,
                                                                                             src_port.id),
                                                           network_id=dst_network.id,
                                                           mac_address=src_port.mac_address,
                                                           fixed_ips=[dst_port_fixed_ip])
        except Exception:
            args.logger.error(f"{func_name}() throws exception while creating an ostack port.",
                              exc_info=True)
    if dst_port:
        return {'port': dst_port.id}

    args.logger.warning(f"{func_name}() Creation of dedicated network port failed! "
                        f"Migrated VM will not have same internal IP address / MAC address. {msg_suffix}")
    return {'uuid': dst_network.id}


def create_dst_server(args, src_server, dst_ostack_conn, dst_project, flavor, keypair, block_device_mappings, server_network_addresses):
    """ create destination server instance """
    # Note: argument network is not valid anymore, use networks
    server_args = {'name': get_dst_resource_name(args, src_server.name),
                   'flavorRef': flavor.id,
                   'block_device_mapping_v2': [{'source_type': 'volume',
                                                'destination_type': 'volume',
                                                'uuid': i_block_device_mapping['destination']['volume_id'],
                                                'device_name': i_block_device_mapping['destination']['device_name'],
                                                'boot_index': 0 if i_block_device_mapping['destination']['volume_bootable'] else None}
                                               for i_block_device_mapping in block_device_mappings],
                   'boot_volume': block_device_mappings[0]['destination']['volume_id'],
                   'networks': [describe_server_network_connection(args,
                                                                   dst_ostack_conn,
                                                                   dst_project,
                                                                   i_netaddr) for i_netaddr in server_network_addresses]}
    if keypair:
        server_args['key_name'] = keypair["name"]                                                              
    log_or_assert(args,
                  "F.35 Destination OpenStack server arguments are generated with valid block-device-mapping",
                  server_args['block_device_mapping_v2'], locals())
    log_or_assert(args,
                  "F.36 Destination OpenStack server arguments are generated with valid network configuration",
                  server_args['networks'], locals())

    server = dst_ostack_conn.compute.create_server(**server_args)
    log_or_assert(args,
                  f"F.37 Destination OpenStack server (name:{server.name}) is created",
                  server, locals())
    server = dst_ostack_conn.compute.wait_for_server(server)
    log_or_assert(args,
                  f"F.38 Destination OpenStack server (name:{server.name}) got ACTIVE",
                  server.status == 'ACTIVE', locals())
    return server


def get_ostack_objstore_containers(ostack_connection):
    """ receive objstore containers """
    return list(ostack_connection.object_store.containers())


def find_ostack_port(ostack_connection, mac_address, ip_address, description_substr='', project=None, network=None, device=None):
    """ find openstack port and narrow down selection with MAC, IP and port description """
    query_ports_args = {}
    if network:
        query_ports_args['network_id'] = network.id
    if project:
        query_ports_args['project_id'] = project.id
    if device:
        query_ports_args['device_id'] = device.id
    project_ports = ostack_connection.network.ports(**query_ports_args)
    return [i_port for i_port in project_ports if i_port.mac_address == mac_address and
            description_substr in i_port.description and
            ip_address in [i_addr.get('ip_address') for i_addr in i_port.fixed_ips]]


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


def get_server_floating_ip_properties(server):
    """ return VM FIP properties (IP type, internal IP addr, FIP addr, MAC addr) """
    int_address_data = {}
    for i_net_name, i_net_addresses in server.addresses.items():
        int_address_data.clear()
        for i_addr_field in i_net_addresses:
            int_ip_type = i_addr_field.get('OS-EXT-IPS:type', 'unknown')
            for i_field_name in ('addr', 'version', 'OS-EXT-IPS-MAC:mac_addr',):
                int_address_data[f"{int_ip_type}/{i_field_name}"] = i_addr_field.get(i_field_name, '?')
        if "fixed/version" in int_address_data and \
                "floating/version" in int_address_data and \
                "fixed/OS-EXT-IPS-MAC:mac_addr" in int_address_data and \
                "floating/OS-EXT-IPS-MAC:mac_addr" in int_address_data and \
                int_address_data["fixed/version"] == int_address_data["floating/version"] and \
                int_address_data["fixed/OS-EXT-IPS-MAC:mac_addr"] == int_address_data["floating/OS-EXT-IPS-MAC:mac_addr"]:
            int_address_data["fixed/network-name"] = i_net_name
            return int_address_data
    return {}


def compare_and_log_projects_quotas(args, log_prefix, src_connection, src_project_id, dst_connection, dst_project_id):
    """ Log quotas comparison for 2 projects. """
    src_quotas = get_project_quotas(src_connection, src_project_id)
    dst_quotas = get_project_quotas(dst_connection, dst_project_id)
    quota_comparison_dict = {
        0: {"logger": args.logger.info, "comment": "Source and destination project quota equal"},
        1: {"logger": args.logger.error, "comment": "Source project quota higher"},
        -1: {"logger": args.logger.warn, "comment": "Destination project quota higher"},
    }
    for i_quota_resource, i_src_quota in src_quotas.items():
        dst_quota = dst_quotas[i_quota_resource]
        comparison_result = compare_quota_values(i_src_quota, dst_quota)
        logger_function = quota_comparison_dict[comparison_result]["logger"]
        comment = quota_comparison_dict[comparison_result]["comment"]
        logger_function(f"{log_prefix} {comment}: {i_quota_resource}, src: {i_src_quota}, dst: {dst_quota}")


# Define sets of names of quotas which we want to check explicitly,
# in order to avoid dealing with irrelevant QuotaSet / Quota properties.
quota_resources_compute = [
    "cores",
    "fixed_ips",
    "injected_file_content_bytes",
    "injected_file_path_bytes",
    "injected_files",
    "instances",
    "key_pairs",
    "metadata_items",
    "ram",
    "server_group_members",
    "server_groups",
]
quota_resources_volume = [
    "backup_gigabytes",
    "backups",
    "gigabytes",
    "groups",
    "per_volume_gigabytes",
    "snapshots",
    "volumes",
]
quota_resources_network = [
    "floating_ips",
    "networks",
    "ports",
    "rbac_policies",
    "routers",
    "security_group_rules",
    "security_groups",
    "subnet_pools",
    "subnets",
]


def get_project_quotas(ostack_connection: openstack.connection.Connection, project_id):
    """ Return all quotas (compute, volume, network) for given project. """
    # compute_quotas = ostack_connection.get_compute_quotas(project_id)
    volume_quotas = ostack_connection.get_volume_quotas(project_id)
    network_quotas = ostack_connection.get_network_quotas(project_id)
    project_quotas = {}
    # project_quotas |= filter_quota_set(quota_resources_compute, compute_quotas)
    project_quotas |= filter_quota_set(quota_resources_volume, volume_quotas)
    project_quotas |= filter_quota_set(quota_resources_network, network_quotas)
    return project_quotas


def filter_quota_set(quota_resources, quotas):
    """ Return a dictionary of quotas filtered by keys in quota_resources """
    return {i_quota_resource: quotas[i_quota_resource] for i_quota_resource in quota_resources}


def compare_quota_values(value_1, value_2):
    """
    Return integer representation of comparison of parameters:
    value_1 == value_2: return 0
    value_1 > value_2: return 1
    value_1 < value_2: return -1

    Treats `None` and `-1` values as unlimited, i.e. always bigger than any other limited value.
    """
    # treat None and -1 as unlimited quota
    val_1 = math.inf if value_1 is None or value_1 == -1 else value_1
    val_2 = math.inf if value_2 is None or value_2 == -1 else value_2
    if val_1 > val_2:
        return 1
    if val_1 < val_2:
        return -1
    return 0


def restore_source_server_status(args, source_project_conn, source_server_detail, source_server):
    """ start server in source cloud (if necessary), wait for VM being back in the same state as at the beginning """
    if source_server_detail.status != source_project_conn.compute.find_server(source_server.id).status and \
            not args.source_servers_left_shutoff:
        if source_server_detail.status == 'ACTIVE':
            source_project_conn.compute.start_server(source_server_detail)
            args.logger.info(f"F.34 Source OpenStack VM server (name:{source_server_detail.name}) requested to start")
        else:
            args.logger.warning(f"F.34 Source OpenStack VM server (name:{source_server_detail.name}) is not in expected state, "
                                f"but migrator does not know how to move to {source_server_detail.status} state")
