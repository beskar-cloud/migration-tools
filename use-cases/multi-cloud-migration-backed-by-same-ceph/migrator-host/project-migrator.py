#!/usr/bin/env python3
"""
OpenStack project multi-cloud migrator

Tool performs OpenStack workflow migration from single OpenStack cloud to another one.
Tool expects same block storage connected to both clouds to be able to perform storage transfer quickly.

Block storage is transferred using external ceph migrator server node using ceph low-level commands.
Ceph migrator server node is allowed to perform ceph operations
(ceph storage access is blocked outside OpenStack servers)
and also provides enough disk space for object storage migration.
TODO: Object storage migration

Tool relies on main libraries:
 * openstacksdk for OpenStack management
 * paramiko     for low-level ceph storage migration (--ceph-migrator-host)

Usage example:
 * Migrate all running virtual servers from source OpenStack ~/c/prod-einfra_cz_migrator.sh.inc
   project meta-cloud-new-openstack into destination one defined by
   OpenRC ~/c/g2-prod-brno-einfra_cz_migrator.sh.inc, validate user's request by
   validating server existence with ID server-id-xyz in spource project
 $ ./project-migrator.py
   --source-openrc                 ~/c/prod-einfra_cz_migrator.sh.inc
   --destination-openrc            ~/c/g2-prod-brno-einfra_cz_migrator.sh.inc
   --project-name                  meta-cloud-new-openstack
   --validation-a-source-server-id server-id-xyz
   --ceph-migrator-sshkeyfile      ~/.ssh/id_rsa.g1-g2-ostack-cloud-migration
"""

import argparse
import logging
import pprint
import sys

import lib
import clib
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
    source_project_type = lib.get_ostack_project_type(source_migrator_conn, source_project)
    lib.log_or_assert(args, "B.02 Source OpenStack cloud project is enabled", source_project.is_enabled)
    lib.log_or_assert(args, f"B.03 Source OpenStack cloud project type is {source_project_type}",
                      source_project_type)

    destination_project = lib.get_ostack_project(destination_migrator_conn, destination_project_name)
    lib.log_or_assert(args, f"B.10 Destination OpenStack cloud project (name:{destination_project_name}) exists", destination_project)
    lib.log_or_assert(args, "B.11 Destination OpenStack cloud project is enabled", destination_project.is_enabled)
    destination_project_type = lib.get_ostack_project_type(destination_migrator_conn, destination_project)
    lib.log_or_assert(args, f"B.12 Destination OpenStack cloud project type is {destination_project_type}",
                      destination_project_type)
    lib.log_or_assert(args, "B.13 Source and destination project types match",
                      source_project_type == destination_project_type)

    if destination_project_type == 'group' and lib.executed_in_ci():
        lib.log_or_assert(args,
                          "B.14 Cloud group project migration is executed by authorized person (cloud/openstack team member).",
                          lib.executed_as_admin_user_in_ci())


    # check user context switching & quotas
    source_project_conn = lib.get_ostack_connection(source_migrator_openrc | {'OS_PROJECT_NAME': source_project.name})
    #source_project_quotas = source_project_conn.get_compute_quotas(source_project.id)
    #lib.log_or_assert(args, f"C.1 Context switching to source OpenStack cloud project succeeded (id:{source_project.id})",
    #              source_project_quotas and source_project_quotas.id == source_project.id)

    destination_project_conn = lib.get_ostack_connection(destination_migrator_openrc | {'OS_PROJECT_NAME': destination_project.name})
    #destination_project_quotas = destination_project_conn.get_compute_quotas(destination_project.id)
    #lib.log_or_assert(args, f"C.2 Context switching to destination OpenStack cloud project succeeded (id:{destination_project.id})",
    #              destination_project_quotas and destination_project_quotas.id == destination_project.id)

    # connect to migrator node
    reply_stdout, reply_stderr, reply_ecode = lib.remote_cmd_exec(args.ceph_migrator_host, args.ceph_migrator_user,
                                                                  args.ceph_migrator_sshkeyfile.name, 'uname -a')
    lib.log_or_assert(args, "D.01 Migrator host is reachable", 'Linux' in reply_stdout and reply_ecode == 0)

    reply_stdout, reply_stderr, reply_ecode = lib.remote_cmd_exec(args.ceph_migrator_host, args.ceph_migrator_user,
                                                                  args.ceph_migrator_sshkeyfile.name,
                                                                  '/root/migrator/ceph-accessible.sh')
    lib.log_or_assert(args, "D.02 Ceph is available from the migrator host", reply_ecode == 0)

    source_rbd_images = {args.source_ceph_ephemeral_pool_name: None,
                         args.source_ceph_cinder_pool_name: None}
    for i_pool_name in source_rbd_images.keys():
        source_rbd_images[i_pool_name] = clib.ceph_rbd_images_list(args, i_pool_name)
        lib.log_or_assert(args, f"D.03 Source cloud RBD images are received ({i_pool_name}).", source_rbd_images[i_pool_name])

    source_keypairs = olib.download_source_keypairs(args)
    lib.log_or_assert(args, "D.04 Source OpenStack cloud keypairs received/downloaded.", source_keypairs)

    source_objstore_containers = olib.get_ostack_objstore_containers(source_project_conn)
    if source_objstore_containers:
        args.logger.warning("D.10 Source OpenStack cloud project contains some object-store containers. " \
                            f"Manual objstore data copy is required. Detected containers:{source_objstore_containers}")
    else:
        args.logger.info("D.10 Source OpenStack cloud project has no object-store containers")

    # get source/destination entities in the project
    source_project_servers = lib.get_ostack_project_servers(source_project_conn, source_project)
    args.logger.info("E.01 Source OpenStack cloud servers received")
    lib.assert_entity_ownership(source_project_servers, source_project)
    args.logger.info(f"E.02 Source OpenStack cloud project has {len(source_project_servers)} servers.")

    destination_project_servers = lib.get_ostack_project_servers(destination_project_conn, destination_project)
    args.logger.info("E.10 Destination OpenStack cloud servers received")
    lib.assert_entity_ownership(destination_project_servers, destination_project)
    args.logger.info(f"E.11 Destination OpenStack cloud project has {len(destination_project_servers)} servers.")

    lib.log_or_assert(args, "E.20 Source OpenStack VM ID validation succeeded",
                      args.validation_a_source_server_id in [i_server.id for i_server in source_project_servers])

    destination_image = destination_project_conn.image.find_image(args.destination_bootable_volume_image_name)
    lib.log_or_assert(args, "E.30 Destination image found and received", destination_image)

    destination_fip_network = destination_project_conn.network.find_network(args.destination_ipv4_external_network)
    lib.log_or_assert(args, "E.31 Destination cloud FIP network detected", destination_fip_network)

    if args.dry_run:
        args.logger.info("Exiting before first cloud modification operation as in dry-run mode.")
        if args.debugging:
            import IPython # on-purpose lazy import
            IPython.embed()
        return

    olib.duplicate_ostack_project_security_groups(args,
                                                  source_project_conn, destination_project_conn,
                                                  source_project, destination_project)
    args.logger.info("E.40 Destination OpenStack project security groups duplicated")

    args.logger.info("F.00 Main looping started")
    args.logger.info(f"F.00 Source VM servers: {[ i_source_server.name for i_source_server in source_project_servers]}")
    for i_source_server in source_project_servers:
        i_source_server_detail = source_project_conn.compute.find_server(i_source_server.id)
        i_source_server_fip_properties = olib.get_server_floating_ip_properties(i_source_server_detail)

        if args.explicit_server_names and i_source_server.name not in args.explicit_server_names:
            args.logger.info(f"F.01 server migration skipped - name:{i_source_server_detail.name} due to --explicit-server-names={args.explicit_server_names}")
            continue

        if i_source_server_detail.status != 'ACTIVE' and not args.migrate_inactive_servers:
            args.logger.info(f"F.01 server migration skipped - name:{i_source_server_detail.name} due to VM status {i_source_server_detail.status}. Use --migrate-inactive-servers=true if necessary.")
            continue
        # detect destination VM does not exist
        i_destination_server_detail = destination_project_conn.compute.find_server(lib.get_dst_resource_name(args, i_source_server_detail.name))
        if i_destination_server_detail:
            args.logger.info(f"F.01 server migration skipped - name:{i_source_server_detail.name} as equivalent VM exists in destination cloud (name: {i_destination_server_detail.name})")
            continue

        args.logger.info(f"F.01 server migration started - name:{i_source_server_detail.name}, id:{i_source_server_detail.id}, " \
                         f"keypair: {i_source_server_detail.key_name}, flavor: {i_source_server_detail.flavor}, " \
                         f"sec-groups:{i_source_server_detail.security_groups}, root_device_name: {i_source_server_detail.root_device_name}, " \
                         f"block_device_mapping: {i_source_server_detail.block_device_mapping}, " \
                         f"attached-volumes: {i_source_server_detail.attached_volumes}" \
                         f"addresses: {i_source_server_detail.addresses}")

        # network/subnet/router detection & creation
        i_destination_server_network_addresses = \
            olib.get_or_create_dst_server_networking(args,
                                                     source_project_conn, destination_project_conn,
                                                     source_project, destination_project,
                                                     i_source_server_detail)

        # flavor detection
        i_destination_server_flavor = olib.get_dst_server_flavor(args,
                                                                 i_source_server_detail,
                                                                 destination_project_conn)

        # keypair detection / creation
        i_destination_server_keypair = olib.get_or_create_dst_server_keypair(args, source_keypairs,
                                                                             i_source_server_detail,
                                                                             destination_project_conn)

        # get / create server security groups
        i_destination_server_security_groups = \
            olib.get_or_create_dst_server_security_groups(args,
                                                          source_project_conn, destination_project_conn,
                                                          source_project, destination_project,
                                                          i_source_server_detail)

        # volume detection, block device mapping creation
        i_server_block_device_mappings = \
            olib.create_server_block_device_mappings(args, source_project_conn,
                                                     i_source_server_detail, source_rbd_images)

        # volume creation in destination cloud
        i_server_block_device_mappings = \
            olib.create_dst_server_volumes_update_block_device_mappings(args,
                                                                        i_server_block_device_mappings,
                                                                        destination_project_conn,
                                                                        destination_image)

        # source VM stop, wait for SHUTOFF
        if i_source_server_detail.status != 'SHUTOFF':
            source_project_conn.compute.stop_server(i_source_server_detail)
            args.logger.info(f"F.33 Source OpenStack VM server (name:{i_source_server_detail.name}) requested to stop")
            lib.log_or_assert(args, f"F.33 Source OpenStack VM server (name:{i_source_server_detail.name}) stopped (reached SHUTOFF state)",
                              lib.wait_for_ostack_server_status(source_project_conn, i_source_server.id, 'SHUTOFF') == "SHUTOFF")

        # volume migration (browse i_server_block_device_mappings)
        for i_server_block_device_mapping in i_server_block_device_mappings:
            clib.migrate_rbd_image(args, i_server_block_device_mapping)

        # start server in source cloud (if necessary), wait for VM being back in the same state as at the beginning
        if i_source_server_detail.status != source_project_conn.compute.find_server(i_source_server.id).status and \
           not args.source_servers_left_shutoff:
            if i_source_server_detail.status == 'ACTIVE':
                source_project_conn.compute.start_server(i_source_server_detail)
                args.logger.info(f"F.34 Source OpenStack VM server (name:{i_source_server_detail.name}) requested to start")
            else:
                args.logger.warning(f"F.34 Source OpenStack VM server (name:{i_source_server_detail.name}) is not in expected state, " \
                                    f"but migrator does not know how to move to {i_source_server_detail.status} state")

        # start server in destination cloud
        i_destination_server = olib.create_dst_server(args,
                                                      i_source_server_detail,
                                                      destination_project_conn,
                                                      destination_project,
                                                      i_destination_server_flavor,
                                                      i_destination_server_keypair,
                                                      i_server_block_device_mappings,
                                                      i_destination_server_network_addresses)

        # add security groups to the destination server (if missing)
        for i_destination_server_security_group_id, i_destination_server_security_group_name in {(i_destination_server_security_group.id, i_destination_server_security_group.name) for i_destination_server_security_group in i_destination_server_security_groups}:
            if {'name': i_destination_server_security_group_name } not in i_destination_server.security_groups:
                destination_project_conn.add_server_security_groups(i_destination_server.id, i_destination_server_security_group_id)
        if args.migrate_fip_addresses and i_source_server_fip_properties:
            # add FIP as source VM has it
            i_destination_server_fip = destination_project_conn.network.create_ip(floating_network_id=destination_fip_network.id)
            lib.log_or_assert(args,
                              f"F.39 Destination OpenStack server (name:{i_destination_server.name}) FIP is created ({i_destination_server_fip.floating_ip_address})",
                              i_destination_server_fip, locals())
            i_destination_server_ports = olib.find_ostack_port(destination_project_conn,
                                                               i_source_server_fip_properties['floating/OS-EXT-IPS-MAC:mac_addr'],
                                                               i_source_server_fip_properties['fixed/addr'],
                                                               project=destination_project)
            lib.log_or_assert(args, f"F.40 Destination OpenStack server (name:{i_destination_server.name}) FIP port(s) are detected",
                              i_destination_server_ports, locals())
            lib.log_or_assert(args, f"F.40 Destination OpenStack server (name:{i_destination_server.name}) single FIP port is detected",
                              len(i_destination_server_ports) == 1, locals())
            i_destination_server_port = i_destination_server_ports[0]
            destination_project_conn.network.add_ip_to_port(i_destination_server_port, i_destination_server_fip)

        args.logger.info(f"F.41 Source OpenStack server name:{i_source_server_detail.name} migrated into destination one name:{i_destination_server.name} id:{i_destination_server.id}")

        if i_source_server_detail.status != source_project_conn.compute.find_server(i_source_server.id).status and \
           not args.source_servers_left_shutoff:
            if i_source_server_detail.status == 'ACTIVE':
                if lib.wait_for_ostack_server_status(source_project_conn, i_source_server.id, i_source_server_detail.status) != i_source_server_detail.status:
                    args.logger.warning(f"F.42 Source OpenStack VM server has not become {i_source_server_detail.status} yet, trying again...")
                    source_project_conn.compute.start_server(i_source_server_detail)
                    args.logger.info(f"F.42 Source OpenStack VM server (name:{i_source_server_detail.name}) requested to start again")
                if lib.wait_for_ostack_server_status(source_project_conn, i_source_server.id, i_source_server_detail.status) != i_source_server_detail.status:
                    args.logger.error(f"F.42 Source OpenStack VM server (name:{i_source_server_detail.name}) has not become " \
                                      f"{i_source_server_detail.status} yet (after second start). " \
                                      f"This situation is no longer asserted but needs manual admin inspection.")
            else:
                args.logger.error(f"F.42 Source OpenStack VM server (name:{i_source_server_detail.name}) is not in proper state, " \
                                  f"but migrator does not know how to move to {i_source_server_detail.status} state")
        else:
            args.logger.info(f"F.42 Source OpenStack VM server (name:{i_source_server_detail.name}) back in expected state {i_source_server_detail.status}.")

    # EXPLICIT OpenStack volume migration
    # ---------------------------------------------------------------------------------------------
    if args.explicit_volume_names:
        for i_source_volume_name in args.explicit_volume_names:
            i_source_volume = source_project_conn.block_storage.find_volume(i_source_volume_name)
            if not i_source_volume:
                args.logger.info(f"H.01 Source volume migration skipped as does not exist (name:{i_source_volume_name})")
                continue
            if i_source_volume.status != 'available':
                args.logger.info(f"H.02 Source volume migration skipped as it is not in state available (name:{i_source_volume_name}, state:{i_source_volume.status}). " \
                                "Note in-use volumes are being migrated in VM server migration part.")
                continue

            i_dst_volume = destination_project_conn.block_storage.create_volume(name=lib.get_dst_resource_name(args, i_source_volume.name),
                                                                                size=i_source_volume.size,
                                                                                description=lib.get_dst_resource_desc(args,
                                                                                                                      i_source_volume.description,
                                                                                                                      i_source_volume.id))
            lib.log_or_assert(args,
                            f"H.03 Destination OpenStack volume created (name:{i_dst_volume.name}, id:{i_dst_volume.id})", i_dst_volume)
            i_dst_volume_status = lib.wait_for_ostack_volume_status(destination_project_conn, i_dst_volume.id, 'available')
            lib.log_or_assert(args,
                            f"H.04 Destination OpenStack volume available (name:{i_dst_volume.name}, id:{i_dst_volume.id})",
                            i_dst_volume_status == 'available')
            i_volume_mapping = {'source':      {'ceph_pool_name': args.source_ceph_cinder_pool_name,
                                                'ceph_rbd_image_name': i_source_volume.id},
                                'destination': {'ceph_pool_name': args.destination_ceph_cinder_pool_name,
                                                'volume_id': i_dst_volume.id}}
            clib.migrate_rbd_image(args, i_volume_mapping)
            i_dst_volume_detail = destination_project_conn.block_storage.find_volume(i_dst_volume.id)
            lib.log_or_assert(args,
                            f"H.05 Destination OpenStack volume available (name:{i_dst_volume_detail.name}, id:{i_dst_volume_detail.id})",
                            i_dst_volume_detail.status == 'available')


# main() call (argument parsing)
# -------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    AP = argparse.ArgumentParser(epilog=globals().get('__doc__'),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    AP.add_argument('--source-openrc', default=None, type=argparse.FileType('r'),
                    required=True, help='Source cloud authentication (OpenRC file)')
    AP.add_argument('--destination-openrc', default=None, type=argparse.FileType('r'),
                    required=True, help='Destination cloud authentication (OpenRC file)')
    AP.add_argument('--ceph-migrator-host', default='controller-ostack.stage.cloud.muni.cz',
                    help='OpenStack migrator ceph node host')
    AP.add_argument('--ceph-migrator-user', default='root',
                    help='OpenStack migrator ceph node username')
    AP.add_argument('--ceph-migrator-sshkeyfile', default=None, type=argparse.FileType('r'),
                    help='OpenStack migrator SSH keyfile')
    AP.add_argument('--ceph-migrator-host-base-dir', default='/root/migrator',
                    help='OpenStack ceph migrator base directory for scripts and operations on ceph mogrator host')
    AP.add_argument('--source-ceph-cinder-pool-name', default='prod-cinder-volumes',
                    help='Source OpenStack/ceph cloud Cinder pool name')
    AP.add_argument('--source-ceph-ephemeral-pool-name', default='prod-ephemeral-vms',
                    help='Source OpenStack/ceph cloud "ephemeral on ceph" or "libvirt ephemeral" pool name')
    AP.add_argument('--destination-ceph-cinder-pool-name', default='cloud-cinder-volumes-prod-brno',
                    help='Destination OpenStack/ceph cloud Cinder pool name')
    AP.add_argument('--destination-ceph-ephemeral-pool-name', default='cloud-ephemeral-volumes-prod-brno',
                    help='Destination OpenStack/ceph cloud "ephemeral on ceph" or "libvirt ephemeral" pool name')
    AP.add_argument('--source-keypair-xml-dump-file', default='/root/migrator/prod-nova_api_key_pairs.dump.xml',
                    help='Source OpenStack cloud keypair SQL/XML dump file name (on ceph-migrator-host)')
    AP.add_argument('--source-servers-left-shutoff', default=False, required=False, action='store_true',
                    help='Migrated source servers are left SHUTOFF (i.e. not started automatically).')
    AP.add_argument('--destination-bootable-volume-image-name', default='cirros-0-x86_64',
                    help='Destination cloud bootable volumes are made on top of public image. Name of destination cloud image.')
    AP.add_argument('--destination-ipv4-external-network', default='external-ipv4-general-public',
                    help='Destination cloud IPV4 external network.')
    AP.add_argument('--destination-secgroup-name-prefix', default='migrated-',
                    help='Destination cloud security_groups entity name prefix.')
    AP.add_argument('--destination-entity-name-prefix', default='',
                    help='Destination cloud entity name prefix (all except secgroups).')
    AP.add_argument('--destination-entity-description-suffix', default=', migrated(id:{})',
                    help='Destination cloud entity description suffix.')

    AP.add_argument('--project-name', default=None, required=True,
                    help='OpenStack project name (identical name in both clouds required)')
    AP.add_argument('--explicit-server-names', default=None, required=False,
                    help='(Optional) List of explicit server names or IDs to be migrated. Delimiter comma or space.')
    AP.add_argument('--explicit-volume-names', default=None, required=False,
                    help='(Optional) List of explicit volume (names or) IDs to be migrated. Delimiter comma or space.')
    AP.add_argument('--migrate-inactive-servers', default=False, required=False, choices=lib.BOOLEAN_CHOICES,
                    help='(Optional) Migrate also inactive servers (i.e. PAUSED/SHUTOFF).')
    AP.add_argument('--migrate-fip-addresses', default=True, required=False, choices=lib.BOOLEAN_CHOICES,
                    help='(Optional) Migrate FIP address[es] when attached to VM under migration.')
    AP.add_argument('--migrate-reuse-already-migrated-volumes', default=False, required=False, choices=lib.BOOLEAN_CHOICES,
                    help='(Optional) Reuse matching already migrated volumes whem migration steps failed after volume transfer (step G17).')
    AP.add_argument('--migrate-volume-snapshots', default=False, required=False, choices=lib.BOOLEAN_CHOICES,
                    help='(Optional) Migrate OpenStack volume snapshots.')

    AP.add_argument('--validation-a-source-server-id', default=None, required=True,
                    help='For validation any server ID from source OpenStack project')

    AP.add_argument('--exception-trace-file', default="project-migrator.dump",
                    required=False,
                    help='Exception / assert dump state file')
    AP.add_argument('--log-level', default="INFO", required=False,
                    choices=[i_lvl for i_lvl in dir(logging) if i_lvl.isupper() and i_lvl.isalpha()],
                    help='Executio log level (python logging)')
    AP.add_argument('--dry-run', default=False, required=False, choices=lib.BOOLEAN_CHOICES,
                    help='Migration dry-run mode. Stop before first modification action.')
    AP.add_argument('--debugging', default=False, required=False, choices=lib.BOOLEAN_CHOICES,
                    help='(Optional) Enter development debugging mode.')

    ARGS = AP.parse_args()
    ARGS.logger = logging.getLogger("project-migrator")
    ARGS.explicit_server_names = lib.get_resource_names_ids(ARGS.explicit_server_names)
    ARGS.explicit_volume_names = lib.get_resource_names_ids(ARGS.explicit_volume_names)
    ARGS.migrate_fip_addresses = str(ARGS.migrate_fip_addresses).lower() == "true"
    ARGS.dry_run = str(ARGS.dry_run).lower() == "true"
    ARGS.debugging = str(ARGS.debugging).lower() == "true"
    ARGS.migrate_reuse_already_migrated_volumes = str(ARGS.migrate_reuse_already_migrated_volumes).lower() == "true"
    ARGS.migrate_volume_snapshots = str(ARGS.migrate_volume_snapshots).lower() == "true"
    ARGS.migrate_inactive_servers = str(ARGS.migrate_inactive_servers).lower() == "true"

    logging.basicConfig(level=getattr(logging, ARGS.log_level),
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')

    sys.exit(main(ARGS))
