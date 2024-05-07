#!/usr/bin/env bash

# ceph-rbd-image-snapshot-delete.sh <ceph-pool-name> <ostack-volume-id> <ostack-snapshot-name>
# returns 0 if RBD image snapshot is deleted

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.cinder"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_POOL="$1"
OSTACK_VOLUME_ID="$2"
OSTACK_SNAPSHOT_NAME="$3"

test -n "${CEPH_POOL}"
test -n "${OSTACK_VOLUME_ID}"
test -n "${OSTACK_SNAPSHOT_NAME}"

RBD_IMAGE="$(rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} ls ${CEPH_POOL} | grep -E "^(volume.)?${OSTACK_VOLUME_ID}(_disk)?$")"

rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} snap unprotect ${CEPH_POOL}/${RBD_IMAGE}@${OSTACK_SNAPSHOT_NAME} || true
rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} snap rm ${CEPH_POOL}/${RBD_IMAGE}@${OSTACK_SNAPSHOT_NAME}
