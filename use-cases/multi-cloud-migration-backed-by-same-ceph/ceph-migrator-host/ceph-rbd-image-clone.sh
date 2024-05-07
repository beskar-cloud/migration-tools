#!/usr/bin/env bash

# ceph-rbd-image-clone.sh <ceph-src-pool-name> <ostack-src-volume-id> <ostack-src-snapshot-id> <ceph-dst-pool-name> <dst-ceph-rbd-image-name>
# returns 0 if RBD clone succeeds

set -eo pipefail

CEPH_CLIENT_DIR="/root/migrator"
CEPH_USER="${CEPH_USER:-"client.cinder"}"
CEPH_KEYRING="${CEPH_CLIENT_DIR}/${CEPH_USER}.keyring"
CEPH_CONFIG="${CEPH_CLIENT_DIR}/ceph.conf"

CEPH_SRC_POOL="$1"
OSTACK_SRC_VOLUME_ID="$2"
OSTACK_SRC_SNAPSHOT_ID="$3"
CEPH_DST_POOL="$4"
CEPH_DST_RBD_IMAGE_NAME="$5"

test -n "${CEPH_SRC_POOL}"
test -n "${OSTACK_SRC_VOLUME_ID}"
test -n "${OSTACK_SRC_SNAPSHOT_ID}"
test -n "${CEPH_DST_POOL}"
test -n "${CEPH_DST_RBD_IMAGE_NAME}"

SRC_RBD_IMAGE="$(rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} ls ${CEPH_SRC_POOL} | grep -E "^(volume.)?${OSTACK_SRC_VOLUME_ID}$")"
SRC_SNAPSHOT_NAME="$(rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} snap ls ${CEPH_SRC_POOL}/${SRC_RBD_IMAGE} | grep -Eo "(snapshot.)?${OSTACK_SRC_SNAPSHOT_ID}")"

rbd --conf="${CEPH_CONFIG}" --name "${CEPH_USER}" --keyring=${CEPH_KEYRING} clone ${CEPH_SRC_POOL}/${SRC_RBD_IMAGE}@${SRC_SNAPSHOT_NAME} ${CEPH_DST_POOL}/${CEPH_DST_RBD_IMAGE_NAME}

