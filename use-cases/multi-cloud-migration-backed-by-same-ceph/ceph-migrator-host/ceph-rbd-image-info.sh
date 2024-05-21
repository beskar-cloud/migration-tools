#!/usr/bin/env bash

# ceph-rbd-image-info.sh <ceph-pool-name> <rbd-image-name>
# returns 0 if RBD image exists and prints its info

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.migrator"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_POOL="$1"
OSTACK_VOLUME_ID="$2"

test -n "${CEPH_POOL}"
test -n "${OSTACK_VOLUME_ID}"

rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} info ${CEPH_POOL}/${OSTACK_VOLUME_ID} --format json

