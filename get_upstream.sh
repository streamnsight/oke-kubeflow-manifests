#!/bin/bash

. ./kubeflow_version.env

CURRENT_DIR=$(pwd)
UPSTREAM_FOLDER="${CURRENT_DIR}/upstream"

# if folder exists
if [ -d "$UPSTREAM_FOLDER" ]
then
    echo "./upstream folder found"
    # Check the tag matches the release
    pushd "$UPSTREAM_FOLDER" > /dev/null || exit 1
    TAG=$(git describe --tags)
    echo "Upstream for version $TAG found"
    popd > /dev/null || exit 1
    # If not, clean up and clone
    if [[ "${TAG}" != "${KUBEFLOW_RELEASE_VERSION}" ]]; then
        echo "Version mismatch"
        rm -rf upstream;
    fi
fi

# upstream was cleared if there was a version mismatch, so if now the folder is not found, new version needs fetching
if [ ! -d "$UPSTREAM_FOLDER" ]
then
    echo "Fetching version ${KUBEFLOW_RELEASE_VERSION} ..."
    git clone -c advice.detachedHead=false --branch ${KUBEFLOW_RELEASE_VERSION} \
        https://github.com/kubeflow/manifests.git --single-branch upstream;
fi
