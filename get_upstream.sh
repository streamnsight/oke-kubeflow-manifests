#!/bin/bash

rm -rf upstream
export KUBEFLOW_RELEASE_VERSION="v1.6.0"
git clone --branch ${KUBEFLOW_RELEASE_VERSION} https://github.com/kubeflow/manifests.git --single-branch upstream
