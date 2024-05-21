#!/usr/bin/env bash

# ceph-rbd-images-list.sh <ceph-pool-name>
# lists all RBD images in a pool and returns 0 if succeedes

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.migrator"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_POOL="$1"
OSTACK_VOLUME_ID="$2"

test -n "${CEPH_POOL}"

rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} ls ${CEPH_POOL}

