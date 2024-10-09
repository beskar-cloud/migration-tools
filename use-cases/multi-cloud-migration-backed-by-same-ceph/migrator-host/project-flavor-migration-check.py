#!/usr/bin/env python3
"""
OpenStack project multi-cloud flavor migration check

Tool performs OpenStack flavor migration check. Helps to build cloud-entities project-quota-acls resource.


Tool relies on main libraries:
 * openstacksdk for OpenStack management

Usage example:
 * Validate that all source VM flavors can be mapped into destination flavors
   Dump cloud-entities§ project-quota-acls resource .acls.flavors snippet
 $ ./project-flavor-migration-check.py
   --source-openrc                 ~/c/prod-einfra_cz_migrator.sh.inc
   --destination-openrc            ~/c/g2-prod-brno-einfra_cz_migrator.sh.inc
   --project-name                  meta-cloud-new-openstack
"""

import argparse
import logging
import sys

import yaml

import lib
import olib


def main(args):
    """ main project migration loop """
    # connect to source cloud
    source_migrator_openrc = lib.get_openrc(args.source_openrc)
    source_migrator_conn = lib.get_ostack_connection(source_migrator_openrc)
    args.logger.info("A.01 Source OpenStack cloud connected as migrator user")

    # connect to destination cloud
    destination_migrator_openrc = lib.get_openrc(args.destination_openrc)
    destination_migrator_conn = lib.get_ostack_connection(destination_migrator_openrc)
    args.logger.info("A.02 Destination OpenStack cloud connected as migrator user")

    # check project exists in source and destination
    source_project_name, destination_project_name = lib.get_ostack_project_names(args.project_name)
    source_project = lib.get_ostack_project(source_migrator_conn, source_project_name)
    lib.log_or_assert(args, f"B.01 Source OpenStack cloud project (name:{source_project_name}) exists", source_project)

    destination_project = lib.get_ostack_project(destination_migrator_conn, destination_project_name)
    if destination_project:
        lib.log_or_assert(args, f"B.10 Destination OpenStack cloud project (name:{destination_project_name}) exists", destination_project)
    else:
        args.logger.warning(f"B.10 Destination OpenStack cloud project (name:{destination_project_name}) does not exist yet")

    # check user context switching & quotas
    source_project_conn = lib.get_ostack_connection(source_migrator_openrc | {'OS_PROJECT_NAME': source_project.name})

    # get source/destination entities in the project
    source_project_servers = lib.get_ostack_project_servers(source_project_conn)
    args.logger.info("E.01 Source OpenStack cloud servers received")
    lib.assert_entity_ownership(source_project_servers, source_project)
    args.logger.info(f"E.02 Source OpenStack cloud project has {len(source_project_servers)} servers.")

    args.logger.info("F.00 Main looping started")
    args.logger.info(f"F.00 Source VM servers: {[i_source_server.name for i_source_server in source_project_servers]}")

    source_flavor_names = []
    destination_expected_flavor_names = []
    for i_source_server in source_project_servers:
        i_source_server_detail = source_project_conn.compute.find_server(i_source_server.id)

        args.logger.info(f"F.01 server evaluation started - name:{i_source_server_detail.name}, "
                         f"flavor: {i_source_server_detail.flavor.name}, addresses: {i_source_server_detail.addresses}, status: {i_source_server_detail.status}")

        # flavor detection
        i_dst_flavor_name = olib.get_dst_server_flavor_name_noassert(args, i_source_server_detail,
                                                                     destination_migrator_conn)
        source_flavor_names.append(i_source_server_detail.flavor.name)
        destination_expected_flavor_names.append(i_dst_flavor_name)

    source_flavor_names = list(set(source_flavor_names))
    source_flavor_names.sort()
    destination_expected_flavor_names = list(set(destination_expected_flavor_names))
    destination_expected_flavor_names.sort()
    args.logger.info(f"F.10 Expected flavor mapping is:\n  source flavors: {source_flavor_names} \n  destination flavors: {destination_expected_flavor_names}")
    args.logger.info("F.11 cloud-entities project acl.flavors should look-like following snippet:\n")
    destination_expected_nonpublic_flavor_names = []
    for i_dst_flavor_name in destination_expected_flavor_names:
        i_dst_flavor = destination_migrator_conn.compute.find_flavor(i_dst_flavor_name)
        if i_dst_flavor and i_dst_flavor.is_public:
            continue
        destination_expected_nonpublic_flavor_names.append(i_dst_flavor.name)

    cld_entities_structure = {'acls': {'flavors': destination_expected_nonpublic_flavor_names}}
    print(yaml.dump(cld_entities_structure))


# main() call (argument parsing)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    AP = argparse.ArgumentParser(epilog=globals().get('__doc__'),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    AP.add_argument('--source-openrc', default=None, type=argparse.FileType('r'),
                    required=True, help='Source cloud authentication (OpenRC file)')
    AP.add_argument('--destination-openrc', default=None, type=argparse.FileType('r'),
                    required=True, help='Destination cloud authentication (OpenRC file)')
    AP.add_argument('--project-name', default=None, required=True,
                    help='OpenStack project name (identical name in both clouds required)')

    AP.add_argument('--exception-trace-file', default="project-migrator.dump",
                    required=False,
                    help='Exception / assert dump state file')
    AP.add_argument('--log-level', default="INFO", required=False,
                    choices=[i_lvl for i_lvl in dir(logging) if i_lvl.isupper() and i_lvl.isalpha()],
                    help='Executio log level (python logging)')

    ARGS = AP.parse_args()
    ARGS.logger = logging.getLogger("project-migrator")
    logging.basicConfig(level=getattr(logging, ARGS.log_level),
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')

    sys.exit(main(ARGS))
