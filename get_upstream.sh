#!/bin/bash

export KUBEFLOW_RELEASE_VERSION="v1.6.0"
CURRENT_DIR=$(pwd)
UPSTREAM_FOLDER="${CURRENT_DIR}/upstream"

# if folder exists
if [ -d "$UPSTREAM_FOLDER" ]
then
    echo "./upstream folder found"
    # Check the tag matches the release
    pushd $UPSTREAM_FOLDER > /dev/null || exit 1
    TAG=$(git describe --tags)
    echo "Upstream for version $TAG found"
    popd > /dev/null || exit 1
    # If not, clean up and clone
    if [[ "${TAG}" != "${KUBEFLOW_RELEASE_VERSION}" ]]; then
        rm -rf upstream;
        git clone --branch ${KUBEFLOW_RELEASE_VERSION} https://github.com/kubeflow/manifests.git --single-branch upstream;
    fi
else
    git clone --branch ${KUBEFLOW_RELEASE_VERSION} https://github.com/kubeflow/manifests.git --single-branch upstream;
fi
