#!/bin/bash

. ./kubeflow.env

# update params.env

if [[ -z "${OCI_KUBEFLOW_OBJECT_STORAGE_REGION}" ]] ; then
  echo "OCI_KUBEFLOW_OBJECT_STORAGE_REGION not set"
fi

if [[ -z "${OCI_KUBEFLOW_OBJECT_STORAGE_ACCESS_KEY}" ]] ; then
  echo "OCI_KUBEFLOW_OBJECT_STORAGE_ACCESS_KEY not set"
fi

if [[ -z "${OCI_KUBEFLOW_OBJECT_STORAGE_SECRET_KEY}" ]] ; then
  echo "OCI_KUBEFLOW_OBJECT_STORAGE_SECRET_KEY not set"
fi

if [[ -z "${OCI_KUBEFLOW_OBJECT_STORAGE_BUCKET}" ]] ; then
  echo "bucket not set"
fi

if [[ -z "${OCI_KUBEFLOW_OBJECT_STORAGE_NAMESPACE}" ]] ; then
  echo "OS Namespace not set"
fi

eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/config.tmpl)\"" > oci/apps/pipeline/oci-object-storage/config
eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/minio.tmpl.env)\"" > oci/apps/pipeline/oci-object-storage/minio.env
eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/params.tmpl.env)\"" > oci/apps/pipeline/oci-object-storage/params.env
