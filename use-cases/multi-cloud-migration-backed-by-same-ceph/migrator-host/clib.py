""" OpenStack migrator - ceph library """

import json
import os.path

from lib import remote_cmd_exec, log_or_assert

def get_ceph_client_name(args, ceph_src_pool_name, ceph_dst_pool_name=None):
    """ identify which ceph user to use for planned ceph operation """
    int_pool_name = ceph_dst_pool_name if ceph_dst_pool_name else ceph_src_pool_name

    return "client.cinder" if int_pool_name in (args.source_ceph_cinder_pool_name, args.source_ceph_ephemeral_pool_name,) else "client.migrator"

def ceph_rbd_images_list(args, pool_name):
    """ list ceph RBD images in pool named pool_name """
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-images-list.sh')
    stdout, _, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                       args.ceph_migrator_user,
                                       args.ceph_migrator_sshkeyfile.name,
                                       f"{script_path} {pool_name}")
    assert stdout, f"RBD pool ({pool_name}) images received successfully (non-empty RBD list)"
    assert ecode == 0, f"RBD pool ({pool_name}) images received successfully (ecode)"
    return stdout.splitlines()

def ceph_rbd_image_info(args, pool_name, rbd_image_name):
    """ get ceph RBD image information """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-info.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name}")
    return json.loads(stdout), stderr, ecode



def ceph_rbd_image_exists(args, pool_name, rbd_image_name):
    """ detect whether RBD image {pool_name}/{rbd_image_name} exists """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-exists.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name}")
    return stdout.splitlines(), stderr, ecode

def ceph_rbd_image_delete(args, pool_name, rbd_image_name):
    """ delete RBD image {pool_name}/{rbd_image_name} """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-delete.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name}")
    return stdout.splitlines(), stderr, ecode

def ceph_rbd_image_flatten(args, pool_name, rbd_image_name):
    """ flatten RBD image {pool_name}/{rbd_image_name} """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-flatten.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name}")
    return stdout.splitlines(), stderr, ecode

def ceph_rbd_image_clone(args, src_pool_name, src_rbd_image_name, src_rbd_image_snapshot_name,
                         dst_pool_name, dst_rbd_image_name):
    """ clone RBD image {src_pool_name}/{src_rbd_image_name}@{src_rbd_image_snapshot_name} -> {dst_pool_name}/{dst_rbd_image_name}"""
    ceph_client_name = get_ceph_client_name(args, src_pool_name, dst_pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-clone.sh')
    cmd = f"CEPH_USER={ceph_client_name} {script_path} {src_pool_name} {src_rbd_image_name} {src_rbd_image_snapshot_name} {dst_pool_name} {dst_rbd_image_name}"
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            cmd)
    return stdout.splitlines(), stderr, ecode

def ceph_rbd_image_copy(args, src_pool_name, src_rbd_image_name, dst_pool_name, dst_rbd_image_name):
    """ copy RBD image {src_pool_name}/{src_rbd_image_name} -> {dst_pool_name}/{dst_rbd_image_name}"""
    ceph_client_name = get_ceph_client_name(args, src_pool_name, dst_pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-copy.sh')
    cmd = f"CEPH_USER={ceph_client_name} {script_path} {src_pool_name} {src_rbd_image_name} {dst_pool_name} {dst_rbd_image_name}"
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            cmd)
    return stdout.splitlines(), stderr, ecode


def ceph_rbd_image_snapshot_exists(args, pool_name, rbd_image_name, rbd_image_snapshot_name):
    """ detect whether RBD image snapshot {pool_name}/{rbd_image_name}@{rbd_image_snapshot_name} exists """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-snapshot-exists.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name} {rbd_image_snapshot_name}")
    return stdout.splitlines(), stderr, ecode

def ceph_rbd_image_snapshot_create(args, pool_name, rbd_image_name, rbd_image_snapshot_name):
    """ create RBD image snapshot {pool_name}/{rbd_image_name}@{rbd_image_snapshot_name} """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-snapshot-create.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name} {rbd_image_snapshot_name}")
    return stdout.splitlines(), stderr, ecode

def ceph_rbd_image_snapshot_delete(args, pool_name, rbd_image_name, rbd_image_snapshot_name):
    """ delete RBD image snapshot {pool_name}/{rbd_image_name}@{rbd_image_snapshot_name} """
    ceph_client_name = get_ceph_client_name(args, pool_name)
    script_path = os.path.join(args.ceph_migrator_host_base_dir, 'ceph-rbd-image-snapshot-delete.sh')
    stdout, stderr, ecode = remote_cmd_exec(args.ceph_migrator_host,
                                            args.ceph_migrator_user,
                                            args.ceph_migrator_sshkeyfile.name,
                                            f"CEPH_USER={ceph_client_name} {script_path} {pool_name} {rbd_image_name} {rbd_image_snapshot_name}")
    return stdout.splitlines(), stderr, ecode

def migrate_rbd_image(args, server_block_device_mapping):
    """ migrate source (G1) ceph RBD image to destination (G2) ceph """

    ## G1: detect existing G1 RBD image
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-exists.sh prod-ephemeral-vms 0069e95e-e805-44ff-bab5-872424312ff6
    source_server_rbd_images, stderr, ecode = ceph_rbd_image_exists(args,
                                                                    server_block_device_mapping['source']['ceph_pool_name'],
                                                                    server_block_device_mapping['source']['ceph_rbd_image_name'])
    log_or_assert(args, "G.01 Source OpenStack VM RBD image exists - query succeeded", ecode == 0, locals())
    log_or_assert(args, "G.01 Source OpenStack VM RBD image exists - single image returned",
                  source_server_rbd_images and len(source_server_rbd_images) == 1, locals())
    source_server_rbd_image = source_server_rbd_images[0]


    ## G2: find volume
    #CEPH_USER=client.migrator ~/migrator/ceph-rbd-image-exists.sh cloud-cinder-volumes-prod-brno <g2-rbd-image-name>
    destination_server_rbd_images, stderr, ecode = ceph_rbd_image_exists(args,
                                                                         server_block_device_mapping['destination']['ceph_pool_name'],
                                                                         server_block_device_mapping['destination']['volume_id'])
    log_or_assert(args, "G.02 Destination OpenStack VM RBD image exists - query succeeded", ecode == 0, locals())
    log_or_assert(args, "G.02 Destination OpenStack VM RBD image exists - single image returned",
                  destination_server_rbd_images and len(destination_server_rbd_images) == 1, locals())
    destination_server_rbd_image = destination_server_rbd_images[0]

    ## G1: create RBD image protected snapshot
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-snapshot-exists.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2 # 1
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-snapshot-create.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2 # 0
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-snapshot-exists.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2 # 0
    source_rbd_image_snapshot_name = f"g1-g2-migration-{source_server_rbd_image}"
    stdout, stderr, ecode = ceph_rbd_image_snapshot_exists(args,
                                                           server_block_device_mapping['source']['ceph_pool_name'],
                                                           source_server_rbd_image,
                                                           source_rbd_image_snapshot_name)
    log_or_assert(args,
                  "G.03 Source OpenStack VM RBD image has non-colliding snapshot " \
                  f"({server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name})",
                  ecode != 0, locals())

    stdout, stderr, ecode = ceph_rbd_image_snapshot_create(args,
                                                           server_block_device_mapping['source']['ceph_pool_name'],
                                                           source_server_rbd_image,
                                                           source_rbd_image_snapshot_name)
    log_or_assert(args,
                  "G.04 Source OpenStack VM RBD image snapshot created " \
                  f"({server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name})",
                  ecode == 0, locals())


    stdout, stderr, ecode = ceph_rbd_image_snapshot_exists(args,
                                                           server_block_device_mapping['source']['ceph_pool_name'],
                                                           source_server_rbd_image,
                                                           source_rbd_image_snapshot_name)
    log_or_assert(args,
                  "G.05 Source OpenStack VM RBD image snapshot exists " \
                  f"({server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name})",
                  ecode == 0, locals())

    ## G2: delete RBD image
    #CEPH_USER=client.migrator ~/migrator/ceph-rbd-image-delete.sh cloud-cinder-volumes-prod-brno <g2-rbd-image-name>
    ## G2: confirm volume is deleted
    #CEPH_USER=client.migrator ~/migrator/ceph-rbd-image-exists.sh cloud-cinder-volumes-prod-brno <g2-rbd-image-name> # 1
    stdout, stderr, ecode = ceph_rbd_image_delete(args,
                                                  server_block_device_mapping['destination']['ceph_pool_name'],
                                                  destination_server_rbd_image)
    log_or_assert(args,
                  f"G.06 Destination OpenStack VM RBD image deletion succeeded ({server_block_device_mapping['destination']['ceph_pool_name']}/{destination_server_rbd_image})",
                  ecode == 0, locals())
    stdout, stderr, ecode = ceph_rbd_image_exists(args,
                                                  server_block_device_mapping['destination']['ceph_pool_name'],
                                                  destination_server_rbd_image)
    log_or_assert(args,
                  f"G.07 Destination OpenStack VM RBD image does not exist ({server_block_device_mapping['destination']['ceph_pool_name']}/{destination_server_rbd_image})",
                  ecode != 0, locals())


    ## G1: clone from snapshot
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-clone.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2 prod-ephemeral-vms migrated-006e230e-df45-4f33-879b-19eada244489_disk
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-exists.sh prod-ephemeral-vms migrated-006e230e-df45-4f33-879b-19eada244489_disk
    source_rbd_cloned_image_name = f"g1-g2-migration-{source_server_rbd_image}"
    stdout, stderr, ecode = ceph_rbd_image_clone(args,
                                                 server_block_device_mapping['source']['ceph_pool_name'],
                                                 source_server_rbd_image,
                                                 source_rbd_image_snapshot_name,
                                                 server_block_device_mapping['source']['ceph_pool_name'],
                                                 source_rbd_cloned_image_name)
    log_or_assert(args,
                  "G.08 Source OpenStack VM RBD image cloned succesfully " \
                  f"({server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name} -> " \
                  f"{server_block_device_mapping['source']['ceph_pool_name']}/{source_rbd_cloned_image_name})",
                  ecode == 0, locals())
    stdout, stderr, ecode = ceph_rbd_image_exists(args,
                                                  server_block_device_mapping['source']['ceph_pool_name'],
                                                  source_rbd_cloned_image_name)
    log_or_assert(args,
                  f"G.09 Source OpenStack VM cloned RBD image exists ({server_block_device_mapping['source']['ceph_pool_name']}/{source_rbd_cloned_image_name})",
                  ecode == 0, locals())

    ## G1: flatten cloned RBD image
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-flatten.sh prod-ephemeral-vms migrated-006e230e-df45-4f33-879b-19eada244489_disk
    stdout, stderr, ecode = ceph_rbd_image_flatten(args,
                                                   server_block_device_mapping['source']['ceph_pool_name'],
                                                   source_rbd_cloned_image_name)
    log_or_assert(args,
                  f"G.10 Source OpenStack VM cloned RBD image flatten successfully ({server_block_device_mapping['source']['ceph_pool_name']}/{source_rbd_cloned_image_name})",
                  ecode == 0, locals())

    ## G1->G2: copy RBD image to target pool
    #CEPH_USER=client.migrator ~/migrator/ceph-rbd-image-copy.sh prod-ephemeral-vms migrated-006e230e-df45-4f33-879b-19eada244489_disk cloud-cinder-volumes-prod-brno <g2-rbd-image-name>
    #CEPH_USER=client.migrator ~/migrator/ceph-rbd-image-exists.sh cloud-cinder-volumes-prod-brno <g2-rbd-image-name> # 0
    stdout, stderr, ecode = ceph_rbd_image_copy(args,
                                                server_block_device_mapping['source']['ceph_pool_name'],
                                                source_rbd_cloned_image_name,
                                                server_block_device_mapping['destination']['ceph_pool_name'],
                                                destination_server_rbd_image)
    log_or_assert(args,
                  "G.11 Source OpenStack VM RBD image copied G1 -> G2 succesfully" \
                  f"{server_block_device_mapping['source']['ceph_pool_name']}/{source_rbd_cloned_image_name} -> " \
                  f"{server_block_device_mapping['destination']['ceph_pool_name']}/{destination_server_rbd_image}",
                  ecode == 0, locals())
    stdout, stderr, ecode = ceph_rbd_image_exists(args,
                                                  server_block_device_mapping['destination']['ceph_pool_name'],
                                                  destination_server_rbd_image)
    log_or_assert(args,
                  f"G.12 Destination OpenStack VM RBD image exists ({server_block_device_mapping['destination']['ceph_pool_name']}/{destination_server_rbd_image})",
                  ecode == 0, locals())

    ## G1: delete cloned RBD image
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-delete.sh prod-ephemeral-vms migrated-006e230e-df45-4f33-879b-19eada244489_disk
    stdout, stderr, ecode = ceph_rbd_image_delete(args,
                                                  server_block_device_mapping['source']['ceph_pool_name'],
                                                  source_rbd_cloned_image_name)
    log_or_assert(args,
                  f"G.13 Source OpenStack VM RBD cloned image deletion succeeded ({server_block_device_mapping['source']['ceph_pool_name']}/{source_rbd_cloned_image_name})",
                  ecode == 0, locals())
    stdout, stderr, ecode = ceph_rbd_image_exists(args,
                                                  server_block_device_mapping['source']['ceph_pool_name'],
                                                  source_rbd_cloned_image_name)
    log_or_assert(args,
                  f"G.14 Source OpenStack VM cloned RBD image does not exist anymore ({server_block_device_mapping['source']['ceph_pool_name']}/{source_rbd_cloned_image_name})",
                  ecode != 0, locals())

    ## G1: remove created snapshot
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-snapshot-exists.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2 # 0
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-snapshot-delete.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2
    #CEPH_USER=client.cinder ~/migrator/ceph-rbd-image-snapshot-exists.sh prod-ephemeral-vms 006e230e-df45-4f33-879b-19eada244489_disk migration-snap2 # 1
    stdout, stderr, ecode = ceph_rbd_image_snapshot_exists(args,
                                                           server_block_device_mapping['source']['ceph_pool_name'],
                                                           source_server_rbd_image,
                                                           source_rbd_image_snapshot_name)
    log_or_assert(args,
                  "G.15 Source OpenStack VM RBD image snapshot still exists " \
                  f"{server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name}",
                  ecode == 0, locals())
    stdout, stderr, ecode = ceph_rbd_image_snapshot_delete(args,
                                                           server_block_device_mapping['source']['ceph_pool_name'],
                                                           source_server_rbd_image,
                                                           source_rbd_image_snapshot_name)
    log_or_assert(args,
                  "G.16 Source OpenStack VM RBD image snapshot deletion succeeeded " \
                  f"{server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name}",
                  ecode == 0, locals())
    stdout, stderr, ecode = ceph_rbd_image_snapshot_exists(args,
                                                           server_block_device_mapping['source']['ceph_pool_name'],
                                                           source_server_rbd_image,
                                                           source_rbd_image_snapshot_name)
    log_or_assert(args,
                  "G.17 Source OpenStack VM RBD image snapshot does not exist anymore " \
                  f"{server_block_device_mapping['source']['ceph_pool_name']}/{source_server_rbd_image}@{source_rbd_image_snapshot_name}",
                  ecode != 0, locals())
