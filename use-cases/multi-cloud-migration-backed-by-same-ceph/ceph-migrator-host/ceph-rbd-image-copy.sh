#!/usr/bin/env bash

# ceph-rbd-image-copy.sh <ceph-src-pool-name> <ostack-src-volume-id> <ceph-dst-pool-name> <dst-ceph-rbd-image-name>
# returns 0 if RBD copy suceeds

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.cinder"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_SRC_POOL="$1"
OSTACK_SRC_VOLUME_ID="$2"
CEPH_DST_POOL="$3"
CEPH_DST_RBD_IMAGE_NAME="$4"

test -n "${CEPH_SRC_POOL}"
test -n "${OSTACK_SRC_VOLUME_ID}"
test -n "${CEPH_DST_POOL}"
test -n "${CEPH_DST_RBD_IMAGE_NAME}"

SRC_RBD_IMAGE="$(rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} ls ${CEPH_SRC_POOL} | grep -E "^(volume.)?${OSTACK_SRC_VOLUME_ID}$")"

rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} cp ${CEPH_SRC_POOL}/${SRC_RBD_IMAGE} ${CEPH_DST_POOL}/${CEPH_DST_RBD_IMAGE_NAME}

