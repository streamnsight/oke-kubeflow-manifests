#!/bin/bash

rm -rf upstream
export KUBEFLOW_RELEASE_VERSION="v1.5.1"
git clone --branch ${KUBEFLOW_RELEASE_VERSION} https://github.com/kubeflow/manifests.git --single-branch upstream
