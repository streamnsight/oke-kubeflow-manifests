#!/bin/bash

. kubeflow.env

# update params.env

if [[ -z "${REGION}" ]] ; then
  echo "Region not set"
fi

if [[ -z "${ACCESSKEY}" ]] ; then
  echo "Region not set"
fi

if [[ -z "${SECRETKEY}" ]] ; then
  echo "Region not set"
fi

if [[ -z "${BUCKET}" ]] ; then
  echo "bucket not set"
fi

if [[ -z "${OSNAMESPACE}" ]] ; then
  echo "OS Namespace not set"
fi

export OCI_REGION=$REGION
export OCI_OS_URL="${OSNAMESPACE}.compat.objectstorage.${REGION}.oraclecloud.com"

eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/config.tmpl)\"" > oci/apps/pipeline/oci-object-storage/config

eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/minio.env.tmpl)\"" > oci/apps/pipeline/oci-object-storage/minio.env

eval "echo \"$(cat oci/apps/pipeline/oci-object-storage/params.env.tmpl)\"" > oci/apps/pipeline/oci-object-storage/params.env
