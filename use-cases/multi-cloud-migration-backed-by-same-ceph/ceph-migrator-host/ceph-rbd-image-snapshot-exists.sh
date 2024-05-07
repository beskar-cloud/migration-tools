#!/usr/bin/env bash

# ceph-rbd-image-snapshot-exists.sh <ceph-pool-name> <ostack-volume-id> <ostack-snapshot-id>
# returns 0 if RBD image snapshot exists and prints its name

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.cinder"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_POOL="$1"
OSTACK_VOLUME_ID="$2"
OSTACK_SNAPSHOT_ID="$3"

test -n "${CEPH_POOL}"
test -n "${OSTACK_VOLUME_ID}"
test -n "${OSTACK_SNAPSHOT_ID}"

RBD_IMAGE="$(rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} ls ${CEPH_POOL} | grep -E "^(volume.)?${OSTACK_VOLUME_ID}$")"

rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} snap ls ${CEPH_POOL}/${RBD_IMAGE} | grep -Eo "(snapshot.)?${OSTACK_SNAPSHOT_ID}"

