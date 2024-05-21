#!/usr/bin/env bash

# ceph-rbd-image-delete.sh <ceph-pool-name> <ostack-volume-id>
# returns 0 if RBD image exists and prints its name

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.migrator"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_POOL="$1"
OSTACK_VOLUME_ID="$2"

test -n "${CEPH_POOL}"
test -n "${OSTACK_VOLUME_ID}"

RBD_IMAGE="$(rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} ls ${CEPH_POOL} | grep -E "^(volume.)?${OSTACK_VOLUME_ID}$")"

if [ -n "${RBD_IMAGE}" ]; then
    rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} rm "${CEPH_POOL}/${RBD_IMAGE}"
fi
