#!/bin/bash

rm -rf upstream
export KUBEFLOW_RELEASE_VERSION="v1.5.0"
git clone --branch ${KUBEFLOW_RELEASE_VERSION} https://github.com/kubeflow/manifests.git --single-branch upstream
