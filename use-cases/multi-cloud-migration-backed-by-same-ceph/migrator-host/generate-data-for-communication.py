#!/usr/bin/env python3
"""
OpenStack project data extractor.

Tool which provides OpenStack project data, which is used to generate email to user. 
It's used in ostack-einfra_cz-trigger-communication-generation pipeline job to generate csv files, which are send to pipeline in kb generate-communication.


Tool relies on main libraries:
 * openstacksdk for OpenStack management

Usage example:
 * Generate csv files which is used for email communication generation.
 $ ./generate-data-for-communication.py
   --source-openrc                 ~/c/prod-einfra_cz_migrator.sh.inc
   --destination-openrc            ~/c/g2-prod-brno-einfra_cz_migrator.sh.inc
   --project-name                  meta-cloud-new-openstack
   --signature                     'John Doe'
   --expiration                    1.1.2025
   --migration-date                2.2.2025
"""

import argparse
import csv
import logging
import sys
from datetime import date

import lib


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
        lib.log_or_assert(args, f"B.02 Destination OpenStack cloud project (name:{destination_project_name}) exists", destination_project)
    else:
        args.logger.warning(f"B.02 Destination OpenStack cloud project (name:{destination_project_name}) does not exist yet")

    # check user context switching & quotas
    source_project_conn = lib.get_ostack_connection(source_migrator_openrc | {'OS_PROJECT_NAME': source_project.name})
    destination_project_conn = lib.get_ostack_connection(destination_migrator_openrc | {'OS_PROJECT_NAME': destination_project.name})

    # get source/destination entities in the project
    source_project_servers = lib.get_ostack_project_servers(source_project_conn)
    args.logger.info("C.01 Source OpenStack cloud servers received")
    lib.assert_entity_ownership(source_project_servers, source_project)

    destination_project_servers = lib.get_ostack_project_servers(destination_project_conn)
    args.logger.info("C.02 Destination OpenStack cloud servers received")
    lib.assert_entity_ownership(destination_project_servers, destination_project)

    # prepare project data
    migration_date = args.migration_date
    vm_count = len(destination_project_servers)
    signature = args.signature
    project_expiration = args.expiration

    project_data = [
        {
            "project_name": source_project_name,
            "migration_date": migration_date,
            "project_expiration": project_expiration,
            "vm_count": vm_count,
            "signature": signature,
            "servers": "servers.csv"
        }
    ]
    args.logger.info("D.01 Basic information about migrated project gathered")

    # prepare server data
    servers_data = []
    for server in destination_project_servers:
        server_info = {
            "g1_name": "",
            "g1_id": "",
            "g1_fip": "",
            "g2_name": server.name,
            "g2_id": server.id,
            "g2_fip": get_fip(server)
        }

        for source_server in source_project_servers:
            dest_server_name = server.name.replace('migrated-', '')
            if source_server.name == dest_server_name:
                server_info['g1_name'] = source_server.name
                server_info['g1_id'] = source_server.id
                server_info['g1_fip'] = get_fip(source_server)
                break
        servers_data.append(server_info)
    args.logger.info("D.02 Information about migrated servers gathered")

    # generate csv files which is lately send to kb job
    data_fieldnames = ["project_name", "migration_date", "project_expiration", "vm_count", "signature", "servers"]
    write_csv("data.csv", data_fieldnames, project_data)
    args.logger.info("E.01 file 'data.csv' containing project data created.")

    servers_fieldnames = ["g1_name", "g1_id", "g1_fip", "g2_name", "g2_id", "g2_fip"]
    write_csv("servers.csv", servers_fieldnames, servers_data)
    args.logger.info("E.02 file 'servers.csv' containing migrated servers data created.")


# Function to write data to a CSV file
def write_csv(file_name, fieldnames, data):
    """ Output CVS data into a file """
    with open(file_name, mode='w', newline='', encoding='utf_8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(data)


def get_fip(server):
    """ Return a floating IP of a server """
    for ip_info_list in server.addresses.values():
        for ip_info in ip_info_list:
            if ip_info.get('OS-EXT-IPS:type') == 'floating':
                return ip_info.get('addr')
    return None


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
    AP.add_argument('--signature', default=None, required=True,
                    help='Signature of person who will be sending the mail.')
    AP.add_argument('--expiration', default=None, required=True,
                    help='Date of expiration of project.')
    AP.add_argument('--migration-date', default=date.today().strftime("%-d.%-m.%Y"), required=False,
                    help='Date of migration of project.')

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
